"""Analyse saved SOF/control/linear-BHIST logs. No transport or device imports."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import statistics

EXPOSURE, GAIN = 0x980911, 0x9e0903
SCHEDULE = [(12,EXPOSURE,1200),(36,EXPOSURE,500),(60,EXPOSURE,1200),
            (84,GAIN,128),(108,GAIN,64),(132,GAIN,128),(156,GAIN,64),
            (180,EXPOSURE,800),(204,EXPOSURE,500)]


def analyse(text, legacy_mode3=False, quality=None):
    suffix = 'parameters-acknowledged' if legacy_mode3 else 'parameter-buffer-submitted'
    pairs = [dict(epoch=int(e),sof=int(s),request=int(r),population=int(p),mean=float(m),submitted=int(a))
             for e,s,r,p,m,a in re.findall(r'Pair epoch=(\d+) sof=(\d+) request=(\d+) population=(\d+) mean=([\d.e+-]+) '+suffix+r'=(\d+)', text)]
    events = [dict(sof=int(a),pending=int(b),event_ns=int(c),observed_ns=int(d))
              for a,b,c,d in re.findall(r'STEPPER_SOF sequence=(\d+) pending=(\d+) event_ns=(\d+) observed_ns=(\d+)',text)]
    writes = [dict(step=int(a),sof=int(b),id=int(c),value=int(d),event_ns=int(e),begin_ns=int(f),end_ns=int(g),ret=int(h),errno=int(i))
              for a,b,c,d,e,f,g,h,i in re.findall(r'CONTROL_WRITE step=(\d+) sof=(\d+) id=(\d+) value=(\d+) event_ns=(\d+) begin_ns=(\d+) end_ns=(\d+) ret=(-?\d+) errno=(\d+)',text)]
    assert events and pairs and len({e['sof'] for e in events})==len(events)
    assert len({p['sof'] for p in pairs})==len(pairs) and len({p['request'] for p in pairs})==len(pairs)
    assert [(w['sof'],w['id'],w['value']) for w in writes]==SCHEDULE
    assert 'STEPPER_RESULT result=0 events=233 steps=9' in text
    assert 'STEPPER_INITIAL_READBACK exposure=500 gain_code=64' in text
    epochs=re.findall(r'APPLICATION_EPOCH epoch=0 frames=(\d+) failed=0 stop=0',text)
    assert len(epochs)==1 and int(epochs[0])>=240
    population = 820560 if legacy_mode3 else 2491136
    assert all(p['epoch']==1 and p['population']==population and p['submitted']==1 for p in pairs)
    if not legacy_mode3:
        modes = re.findall(r'STEPPER_MODE width=4208 height=2368 code=\d+ crop=0,376,4208,2368 hblank=640 vblank=944 pixel_rate=481930000 test_pattern=0',text)
        assert len(modes)==2, 'Configure and SOF0 mode2 guards required'
        assert 'delayed-controls=0' in text
        assert not re.search(r'(?:AGC_APPLY|Automatic sensor update|SENSOR_WRITE)',text), 'Unexpected automatic-control trace'
    means = {p['sof']:p['mean'] for p in pairs}
    event_map = {e['sof']:e for e in events}
    periods = [b['event_ns']-a['event_ns'] for a,b in zip(events,events[1:]) if b['sof']==a['sof']+1]
    assert periods and all(p>0 for p in periods)
    period = statistics.median(periods)
    quality = quality or {}
    results = []; previous = {EXPOSURE:500, GAIN:64}
    for w in writes:
        n=w['sof']; direction='up' if w['value']>previous[w['id']] else 'down'; previous[w['id']]=w['value']
        row=dict(step=w['step'],sof=n,control='exposure' if w['id']==EXPOSURE else 'analogue_gain',direction=direction,value=w['value'],
                 write_start_after_sof_us=(w['begin_ns']-w['event_ns'])/1000,
                 write_duration_us=(w['end_ns']-w['begin_ns'])/1000,
                 useful_response=False,first_observed_changed_offset=None,first_three_frame_plateau_offset=None)
        needed=set(range(n-6,n))|set(range(n,n+8))|set(range(n+6,n+14))
        reason=[]
        if not needed<=means.keys(): reason.append('missing-paired-sof')
        if n not in event_map or event_map[n]['event_ns']!=w['event_ns'] or event_map[n]['pending']: reason.append('event-mismatch-or-pending')
        if w['ret'] or w['errno'] or not w['event_ns']<=w['begin_ns']<=w['end_ns']:reason.append('failed-or-invalid-write')
        if n+1 not in event_map or w['end_ns']>=event_map[n+1]['event_ns']:reason.append('write-crossed-next-sof')
        if any(quality.get(str(s),{}).get('saturated') for s in needed):reason.append('known-saturation')
        if any(means.get(s,0)>=1023 for s in needed):reason.append('full-scale-mean')
        if reason:
            row['invalid_reasons']=reason;results.append(row);continue
        before=[means[x] for x in range(n-6,n)];after=[means[x] for x in range(n+6,n+14)]
        pre=statistics.median(before);post=statistics.median(after);delta=post-pre
        mad=lambda values,median:statistics.median(abs(v-median) for v in values)
        noise=max(mad(before,pre),mad(after,post),.000001)
        usable=abs(delta)>10*noise and abs(delta)>max(abs(pre),abs(post))*.05
        response=[(means[n+k]-pre)/delta if delta else None for k in range(8)]
        first=next((k for k in range(6) if all(.15<=r<=1.5 for r in response[k:k+3])),None) if usable else None
        settled=next((k for k in range(6) if all(.85<=r<=1.15 for r in response[k:k+3])),None) if usable else None
        row.update(pre_median=pre,post_median=post,robust_noise=noise,normalized_response=response,
                   useful_response=usable,first_observed_changed_offset=first,first_three_frame_plateau_offset=settled,
                   invalid_reasons=[] if usable else ['original-low-snr-or-small-response'])
        results.append(row)
    groups={}
    for name in ['exposure','analogue_gain']:
        groups[name]={direction:[dict(step=r['step'],first=r['first_observed_changed_offset'],plateau=r['first_three_frame_plateau_offset'])
                      for r in results if r['control']==name and r['direction']==direction and r['useful_response']]
                      for direction in ['up','down']}
    return dict(stage=476,source_mode=3 if legacy_mode3 else 2,cache_regression_only=legacy_mode3,
        paired_images=len(pairs),application_frames=int(epochs[0]),all_application_frames_paired=len(pairs)==int(epochs[0]),
        observed_sofs=len(events),frame_period_ns=period,
        pair_field=suffix,statistics_domain='same-SOF full-input linear BHIST',population=population,
        no_delay_input_or_expected_delay=True,mode2_physical_delay_proven=False,
        saturation_note='Known saturation sidecar/full-scale means rejected; partial clipping cannot be proved absent from means alone',
        per_control_and_direction=groups,changes=results)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True,help='Private output: contains scene measurements')
    parser.add_argument('--quality',type=Path,help='Optional per-SOF known-saturation facts; never a guessed status')
    args=parser.parse_args()
    data=analyse(args.log.read_text(errors='replace'),quality=json.loads(args.quality.read_text()) if args.quality else None)
    data['log_sha256']=hashlib.sha256(args.log.read_bytes()).hexdigest()
    args.output.write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps(dict(source_mode=data['source_mode'],paired_images=data['paired_images'],
         useful_steps=sum(r['useful_response'] for r in data['changes']),no_delay_preset=True,output=str(args.output))))


if __name__=='__main__':main()
