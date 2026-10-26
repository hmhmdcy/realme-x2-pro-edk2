"""Recompute full histograms and report evidence, without declaring scene quality."""
from pathlib import Path
import json
import math
import re

R=Path(__file__).resolve().parent
P=Path('/mnt/e/edk2-samurai-out/kernel240')
report=json.loads((R/'upright-r2-validation.json').read_text())
logs=json.loads((P/'upright-r2-parameter-log-lines-private.json').read_text())
assert report['diagnostic_capture_completed'] and len(report['frames'])==24
assert len(logs['processing'])==len(logs['debayer'])==len(logs['captured'])==24


def verify(measurement,count):
    hist=dict(measurement['histogram'])
    assert len(hist)==len(measurement['histogram']) and sum(hist.values())==measurement['samples']==count
    assert all(n>0 for n in hist.values())
    mean=sum(value*n for value,n in hist.items())/count
    variance=sum(value*value*n for value,n in hist.items())/count-mean*mean
    deviation=math.sqrt(max(0,variance))
    assert abs(measurement['mean']-mean)<.001 and abs(measurement['stddev']-deviation)<.001
    assert measurement['min']==min(hist) and measurement['max']==max(hist)
    return mean,deviation,hist


rows=[]
for i,(frame,identity,parameters,captured) in enumerate(zip(report['frames'],logs['processing'],logs['debayer'],logs['captured'])):
    assert frame['queued_index']==i and frame['sequence']==frame['raw_sequence'] and frame['timestamp_ns']==frame['raw_timestamp_ns']
    if i:
        assert frame['sequence']>report['frames'][i-1]['sequence'] and frame['timestamp_ns']>report['frames'][i-1]['timestamp_ns']
    parsed=re.search(r'Processing frame (\d+), sequence (\d+), timestamp (\d+)',identity)
    frame_id,sequence,timestamp=map(int,parsed.groups())
    assert sequence==frame['sequence'] and timestamp==frame['timestamp_ns']
    captured_id,captured_seq,_=map(int,re.search(r'Captured request (\d+) from sequence (\d+), control sequence (\d+)',captured).groups())
    assert (captured_id,captured_seq)==(frame_id,sequence)
    assert re.search(r'\] \[(\d+)\] DEBUG Debayer',identity)[1]==re.search(r'\] \[(\d+)\] DEBUG Debayer',parameters)[1]
    black=[float(v) for v in re.search(r'blackLevel=Vector \{ ([^}]+)\}',parameters)[1].split(',')]
    raw_mean,raw_std,raw_hist=verify(frame['raw'],1632*1224)
    rgb_mean,rgb_std,rgb_hist=verify(frame['rgb'],1624*1224*3)
    high8={}
    for value,count in raw_hist.items():high8[value>>2]=high8.get(value>>2,0)+count
    assert high8==dict(frame['raw']['high8_histogram'])
    bayer=[verify(m,1632*1224//4)[:2] for m in frame['bayer']]
    channels=[verify(m,1624*1224)[:2] for m in frame['rgb_channels']]
    assert len(bayer)==4 and len(channels)==3
    rows.append(dict(queued_index=i,source_sequence=sequence,paired_sequence_timestamp_verified=True,
        exposure_us=frame['exposure_us'],analogue_gain=frame['analogue_gain'],
        raw_min=min(raw_hist),raw_max=max(raw_hist),raw_mean=raw_mean,raw_stddev=raw_std,
        raw_at_most80_fraction=sum(n for v,n in raw_hist.items() if v<=80)/(1632*1224),
        raw_above128_fraction=sum(n for v,n in raw_hist.items() if v>128)/(1632*1224),
        raw_saturated_at_least1000_fraction=sum(n for v,n in raw_hist.items() if v>=1000)/(1632*1224),
        bayer_phase_means=[v[0] for v in bayer],bayer_phase_stddevs=[v[1] for v in bayer],
        applied_blc_8bit=[round(v*255) for v in black],
        rgb_min=min(rgb_hist),rgb_max=max(rgb_hist),rgb_mean=rgb_mean,rgb_stddev=rgb_std,
        rgb_channel_means=[v[0] for v in channels],rgb_channel_stddevs=[v[1] for v in channels],
        rgb_zero_fraction=rgb_hist.get(0,0)/(1624*1224*3),rgb_all_zero=frame['all_zero']))
phases=[]
for phase,start,exposure in [(0,6,2000),(1,18,32000)]:
    selected=rows[start:start+6]
    assert len(selected)==6 and all(abs(r['exposure_us']-exposure)<50 and abs(r['analogue_gain']-1)<.03 for r in selected)
    means=lambda key:sum(r[key] for r in selected)/6
    phases.append(dict(phase=phase,settled_queued_indices=list(range(start,start+6)),
        measured_exposure_us=means('exposure_us'),raw_mean=means('raw_mean'),raw_pixel_stddev=means('raw_stddev'),
        raw_min=min(r['raw_min'] for r in selected),raw_max=max(r['raw_max'] for r in selected),
        raw_at_most80_fraction=means('raw_at_most80_fraction'),raw_above128_fraction=means('raw_above128_fraction'),
        rgb_mean=means('rgb_mean'),rgb_min=min(r['rgb_min'] for r in selected),rgb_max=max(r['rgb_max'] for r in selected),
        rgb_zero_fraction=means('rgb_zero_fraction'),
        rgb_channel_means=[sum(r['rgb_channel_means'][j] for r in selected)/6 for j in range(3)],
        bayer_phase_means=[sum(r['bayer_phase_means'][j] for r in selected)/6 for j in range(4)]))
result=dict(stage=240,user_reported_upright=True,paired24_and_full_histograms_recomputed=True,
    every_processing_identity_matches_callback=True,default_r15_runtime=True,
    all_cleanup_verified=not report['restore_errors'] and not any(report['fault_delta'].values()),
    raw_rgb_different_crop_no_pixelwise_equivalence_claim=True,
    strict_nonzero_pass=report['strict_nonzero_frames_passed'],zero_indices=[r['queued_index'] for r in rows if r['rgb_all_zero']],
    phase_summaries=phases,frames=rows,scene_optical_response_and_colour_acceptance_not_inferred_from_nonzero=True,
    channel_indices_follow_memory_layout_no_red_blue_assignment_claim=True,no_scene_images_saved=True)
(R/'upright-analysis.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='frames'}))
