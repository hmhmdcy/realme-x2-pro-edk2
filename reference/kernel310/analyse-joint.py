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
'''.replace('ROOT',repr('/var/lib/samurai/k310-joint-'+run))
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=30)
(host.PRIVATE/('joint-'+run+'-results.json')).write_bytes(q.stdout)
data=json.loads(q.stdout)
if not data['state']['terminal'] or data['worker_live']:raise RuntimeError('Worker still live; inspect the same run')
report={'stage':310,'run':run,'capture':data['state']['summary'],'sensors':{}}
def quantize(value,norm):
    q=lambda v:min((math.floor(v*1024+.5)+4)>>3,4095)
    return q(value*norm)/q(norm)
for model,text in data['logs'].items():
    norm=1.0 if model=='imx319' else 1.06201171875
    sony=model in ['imx319','imx471']
    gain=lambda code:1024/(1024-code) if sony else code/32
    configured=re.findall(r'Sensor configuration model=\S+ pixel-rate=(\d+) line-length=(\d+) frame-length=(\d+)',text)
    if not configured:
        report['sensors'][model]={'errors':['No sensor timing context'],'epochs':[]};continue
    rate,line,frame=map(int,configured[-1]);lineUs=line*1e6/rate
    contexts={(int(e),int(s)):(int(v),int(x),int(g),int(c)) for e,s,v,x,g,c in re.findall(
        r'SensorContext epoch=(\d+) sof=(\d+) valid=(\d+) exposure-lines=(\d+) gain-code=(\d+) source=(\d+)',text)}
    pairs=[(int(e),int(s),int(r),int(p),float(m),int(a)) for e,s,r,p,m,a in re.findall(
        r'Pair epoch=(\d+) sof=(\d+) request=(\d+) population=(\d+) mean=([\d.e+-]+) parameters-acknowledged=(\d+)',text)]
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
    errors=[];actual={};means={};first={};trace=[];current=None
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
        if not v or p<=0 or a!=1 or meta[0]!=math.floor(x*lineUs+.5) or abs(meta[1]-gain(g))>5e-6*max(1,gain(g)) or meta[2:]!=(0,0):
            errors.append({'epoch':e,'sof':s,'reason':'sensor metadata mismatch'})
        eligible=[(start,revision) for ep,start,revision in acks if ep==e and start<=s]
        if not eligible:errors.append({'epoch':e,'sof':s,'reason':'missing WB confirmation'});continue
        _,revision=max(eligible)
        wanted=queued.get((e,revision)) if revision else ((4.,.5) if e==1 else (.5,4.))
        if wanted is None or wbContexts.get((e,s))!=(revision,1) or any(abs(x-quantize(y,norm))>1e-5 for x,y in zip(white[:2],wanted)):
            errors.append({'epoch':e,'sof':s,'reason':'WB metadata mismatch'})
        if c!=0xffffffff:
            proposal=updates.get((e,c))
            if not proposal or proposal[1:]!=(x,g):errors.append({'epoch':e,'sof':s,'reason':'unknown AE revision'})
            first.setdefault((e,c),s)
        actual[e,s]=(x,g,c);means[e,s]=m/1023
    missingWrites=[]
    for (e,c),s in first.items():
        x,g,_=actual[e,s]
        for name,value in [('Exposure',x),('Analogue Gain',g)]:
            if (e,s-2,name,value) not in trace:missingWrites.append((e,s-2,name,value))
    physical=[]
    for (e,c),s in first.items():
        if any((e,k) not in actual for k in range(s-3,s+3)):continue
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
    if len(set((e,s) for e,s,*_ in pairs))!=len(pairs):errors.append('Duplicate SOF pair')
    report['sensors'][model]={'frames':len(pairs),'errors':errors,'missing_write_at_effective_minus2':missingWrites,
        'real_control_writes_verified':2*len(first)-len(missingWrites),'epochs':epochs,'physical_bhist_responses':physical,
        'useful_physical_responses':sum(r['useful'] for r in physical),'aligned_physical_responses':sum(r['first_response_aligned'] for r in physical),
        'post_wb_image_luma_not_used_as_independent_ae_timing':True}
report['metadata_and_control_timing_passed']=all(not s['errors'] and not s.get('missing_write_at_effective_minus2') for s in report['sensors'].values())
report['all_eight_streams_reached_target']=len(report['sensors'])==4 and all(len(s['epochs'])==2 and all(e['final8_within_0_01_of_target'] and e['final8_sensor_controls_stable'] and e['locked_frames']>=8 for e in s['epochs']) for s in report['sensors'].values())
report['passed']=report['capture']['passed'] and report['metadata_and_control_timing_passed'] and report['all_eight_streams_reached_target']
report['formal_iq_calibration_complete']=False
(HERE/('joint-'+run+'-validation.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='capture'},indent=2))
