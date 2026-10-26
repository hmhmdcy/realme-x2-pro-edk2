"""Check per-SOF sensor/WB metadata and measured control timing for each stream."""
from pathlib import Path
import json,math,re,shlex,statistics,sys
import host
HERE=Path(__file__).resolve().parent
run=sys.argv[1] if len(sys.argv)>1 else 'r1'
code=r'''
from pathlib import Path
import json
root=Path(ROOT);state=json.loads((root/'state.json').read_text())
p=Path('/proc',str(state['pid']),'stat')
live=p.exists() and p.read_text().rsplit(')',1)[1].split()[0]!='Z'
print(json.dumps({'state':state,'worker_live':live,'logs':{p.stem.removeprefix('capture-'):p.read_text(errors='replace') for p in root.glob('capture-*.log')}}))
'''.replace('ROOT',repr('/var/lib/samurai/k312-joint-'+run))
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=30)
(host.PRIVATE/('joint-'+run+'-results.json')).write_bytes(q.stdout)
data=json.loads(q.stdout)
if not data['state']['terminal'] or data['worker_live']:raise RuntimeError('Worker still live; inspect the same run')
report={'stage':312,'run':run,'capture':data['state']['summary'],'sensors':{}}
def quantize(value,norm):
    q=lambda v:min((math.floor(v*1024+.5)+4)>>3,4095)
    return q(value*norm)/q(norm)
for label,text in data['logs'].items():
    model=label.split('-',1)[0]
    norm=1.0 if model=='imx319' else 1.06201171875
    proposalPrecision=17 if 'precision=17' in text else 6
    sony=model in ['imx319','imx471']
    gain=lambda code:1024/(1024-code) if sony else code/32
    configured=re.findall(r'Sensor configuration model=\S+ pixel-rate=(\d+) line-length=(\d+) frame-length=(\d+)',text)
    if not configured:
        report['sensors'][label]={'errors':['No sensor timing context'],'epochs':[]};continue
    rate,line,frame=map(int,configured[-1]);lineUs=line*1e6/rate
    contexts={(int(e),int(s)):(int(v),int(x),int(g),int(c)) for e,s,v,x,g,c in re.findall(
        r'SensorContext epoch=(\d+) sof=(\d+) valid=(\d+) exposure-lines=(\d+) gain-code=(\d+) source=(\d+)',text)}
    pairs=[(int(e),int(s),int(r),int(p),float(m),int(a)) for e,s,r,p,m,a in re.findall(
        r'Pair epoch=(\d+) sof=(\d+) request=(\d+) population=(\d+) mean=([\d.e+-]+) parameters-acknowledged=(\d+)',text)]
    fallback=[(int(e),int(s),int(r),0,None,1) for e,s,r in re.findall(r'Image controls recovered epoch=(\d+) sof=(\d+) request=(\d+)',text)]
    fallbackKeys={(e,s) for e,s,*_ in fallback}
    pairs=sorted(pairs+fallback,key=lambda row:row[:2])
    metadata={(int(e)+1,int(r)):(int(x),float(g),int(em),int(gm)) for e,r,x,g,em,gm in re.findall(
        r'APPLICATION_SENSOR_METADATA epoch=(\d+) request=(\d+) exposure_us=(\d+) analogue_gain=([\d.e+-]+) exposure_mode=(\d+) gain_mode=(\d+)',text)}
    wb={(int(e)+1,int(r)):(float(a),float(b),int(l)) for e,r,a,b,l in re.findall(
        r'APPLICATION_WB epoch=(\d+) request=(\d+) red=([\d.e+-]+) blue=([\d.e+-]+) locked=(\d+)',text)}
    wbContexts={(int(e),int(s)):(int(v),int(k)) for e,s,v,k in re.findall(
        r'WB context epoch=(\d+) sof=(\d+) revision=(\d+) known=(\d+)',text)}
    queued={(int(e),int(v)):(float(r),float(b)) for e,v,r,b in re.findall(
        r'WB queue epoch=(\d+) revision=(\d+) red=([\d.e+-]+) blue=([\d.e+-]+)',text)}
    acks=[(int(e),int(s),int(v)) for e,s,v in re.findall(r'Parameters epoch=(\d+) first-sof=(\d+) revision=(\d+)',text)]
    updates={(int(e),int(v)):(int(s),int(x),int(g)) for e,s,v,x,g in re.findall(
        r'AE update epoch=(\d+) stats-sof=(\d+) revision=(\d+) exposure-lines=(\d+) gain-code=(\d+)',text)}
    errors=[];actual={};means={};first={};trace=[];current=None;ambiguous=[]
    def possible_quantized(value):
        half=0 if not value else .5*10**(math.floor(math.log10(abs(value)))-proposalPrecision+1)
        green=(math.floor(norm*1024+.5)+4)>>3
        a=round(quantize(max(0,value-half),norm)*green);b=round(quantize(value+half,norm)*green)
        return [n/green for n in range(a,b+1)]
    for row in text.splitlines():
        m=re.search(r'SOF epoch=(\d+) sequence=(\d+)',row)
        if m:current=(int(m[1]),int(m[2]))
        m=re.search(r'DelayedControls .*Setting (Exposure|Analogue Gain) to (\d+) at index',row)
        if m and current:trace.append((*current,m[1],int(m[2])))
    for e,s,r,p,m,a in pairs:
        context=contexts.get((e,s));meta=metadata.get((e,r));white=wb.get((e,r))
        if not context or not meta or not white:
            errors.append({'epoch':e,'sof':s,'reason':'missing context or metadata'});continue
        v,x,g,c=context
        if not v or (m is not None and p<=0) or a!=1 or meta[0]!=math.floor(x*lineUs+.5) or abs(meta[1]-gain(g))>5e-6*max(1,gain(g)) or meta[2:]!=(0,0):
            errors.append({'epoch':e,'sof':s,'reason':'sensor metadata mismatch'})
        eligible=[(start,revision) for ep,start,revision in acks if ep==e and start<=s]
        if not eligible:errors.append({'epoch':e,'sof':s,'reason':'missing WB confirmation'});continue
        _,revision=max(eligible)
        wanted=queued.get((e,revision)) if revision else (1.,1.)
        possible=[possible_quantized(y) for y in wanted] if wanted else []
        if wanted is None or ((e,s) not in fallbackKeys and wbContexts.get((e,s))!=(revision,1)) or any(not any(abs(x-y)<1e-5 for y in values) for x,values in zip(white[:2],possible)):
            errors.append({'epoch':e,'sof':s,'reason':'WB metadata mismatch'})
        if any(len(values)>1 for values in possible):ambiguous.append({'epoch':e,'sof':s,'revision':revision})
        if c!=0xffffffff:
            proposal=updates.get((e,c))
            if not proposal or proposal[1:]!=(x,g):errors.append({'epoch':e,'sof':s,'reason':'unknown AE revision'})
            first.setdefault((e,c),s)
        actual[e,s]=(x,g,c)
        if m is not None:means[e,s]=m/1023
    # Control writes continue during a temporary image-buffer gap; use all SOF contexts.
    for (e,s),(valid,x,g,c) in sorted(contexts.items()):
        if valid and c!=0xffffffff and (e,c) in updates:
            first[(e,c)]=min(first.get((e,c),s),s)
    missingWrites=[]
    for (e,c),s in first.items():
        _,x,g,_=contexts[e,s]
        for name,value in [('Exposure',x),('Analogue Gain',g)]:
            if (e,s-2,name,value) not in trace:missingWrites.append((e,s-2,name,value))
    physical=[]
    for (e,c),s in first.items():
        if any((e,k) not in actual or (e,k) not in means for k in range(s-3,s+3)):continue
        old,new=actual[e,s-1],actual[e,s]
        ratio=new[0]*gain(new[1])/(old[0]*gain(old[1]))
        preValues=[means[e,k] for k in range(s-3,s)];postValues=[means[e,k] for k in range(s,s+3)]
        pre,post=statistics.median(preValues),statistics.median(postValues);delta=post-pre
        noise=max(statistics.median(abs(v-pre) for v in preValues),statistics.median(abs(v-post) for v in postValues),1e-7)
        useful=abs(delta)>6*noise and abs(delta)>.005*max(abs(pre),abs(post),1e-7)
        direction=(ratio-1)*delta>0
        aligned=useful and direction and abs(means[e,s-1]-pre)<.15*abs(delta) and all((v-pre)/delta>=.15 for v in postValues)
        physical.append({'epoch':e,'revision':c,'effective_sof':s,'useful':useful,'response_direction_matches_ev':direction,'first_response_aligned':aligned})
    epochs=[]
    for e in sorted(set(ep for ep,*_ in pairs)):
        rows=[row for row in pairs if row[0]==e];last=rows[-8:]
        tail=[means[e,s] for _,s,*_ in last if (e,s) in means]
        wbs=[wb[e,r] for _,_,r,*_ in rows if (e,r) in wb]
        sensorTail=[metadata[e,r][:2] for _,_,r,*_ in last if (e,r) in metadata]
        epochs.append({'epoch':e,'frames':len(rows),'ae_proposals':sum(ep==e for ep,c in updates),
            'effective_ae_revisions':sum(ep==e for ep,c in first),'wb_parameter_updates':sum(ep==e and rev>0 for ep,s,rev in acks),
            'locked_frames':sum(bool(w[2]) for w in wbs),'last_wb':wbs[-1] if wbs else None,
            'final8_mean_luminance':statistics.mean(tail) if tail else None,
            'final8_within_0_01_of_target':len(tail)==8 and all(abs(v-.16)<.01 for v in tail),
            'final8_sensor_controls_stable':len(sensorTail)==8 and len(set(sensorTail))==1,
            'final_sensor':sensorTail[-1] if sensorTail else None})
    if len(pairs)!=len(metadata) or len(pairs)!=len(wb):errors.append('Frame metadata count differs')
    if len(pairs)!=text.count('APPLICATION_FRAME '):errors.append('Completed application images differ from described frames')
    if len(set((e,s) for e,s,*_ in pairs))!=len(pairs):errors.append('Duplicate SOF pair')
    width,height=map(int,label.split('-',1)[1].split('x'))
    if any(m is not None and p!=width*height//4 for e,s,r,p,m,a in pairs):errors.append('Statistics population differs from requested sensor mode')
    report['sensors'][label]={'frames':len(pairs),'requested_mode':[width,height],'configured_timing':[rate,line,frame],
        'proposal_log_significant_digits':proposalPrecision,
        'image_request_mapping_resyncs':[(int(a),int(b)) for a,b in re.findall(r'Resynced image/request mapping old=(-?\d+) new=(-?\d+)',text)],
        'buffer_hold_resumed':'APPLICATION_BUFFER_RESUMED after_hold_ms=120' in text,
        'frames_recovered_without_statistics':len(fallback),
        'rounded_proposal_quantization_ambiguous_frames':ambiguous,'errors':errors,'missing_write_at_effective_minus2':missingWrites,
        'real_control_writes_verified':2*len(first)-len(missingWrites),'epochs':epochs,'physical_bhist_responses':physical,
        'useful_physical_responses':sum(r['useful'] for r in physical),'aligned_physical_responses':sum(r['first_response_aligned'] for r in physical),
        'post_wb_image_luma_not_used_as_independent_ae_timing':True}
report['metadata_and_control_timing_passed']=all(not s['errors'] and not s.get('missing_write_at_effective_minus2') for s in report['sensors'].values())
report['all_six_modes_reached_target']=len(report['sensors'])==6 and all(len(s['epochs'])==1 and all(e['final8_within_0_01_of_target'] and e['final8_sensor_controls_stable'] and e['locked_frames']>=8 for e in s['epochs']) for s in report['sensors'].values())
report['all_reported_modes_reached_target']=all(len(s['epochs'])==1 and all(e['final8_within_0_01_of_target'] and e['final8_sensor_controls_stable'] and e['locked_frames']>=8 for e in s['epochs']) for s in report['sensors'].values())
report['passed']=report['capture']['passed'] and report['metadata_and_control_timing_passed'] and report['all_reported_modes_reached_target']
report['formal_iq_calibration_complete']=False
(HERE/('default-'+run+'-validation.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='capture'},indent=2))
