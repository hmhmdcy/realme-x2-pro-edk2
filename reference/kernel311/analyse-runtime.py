"""Relate runtime requests, ISP confirmations, per-frame metadata and pixels."""
from pathlib import Path
import json,math,re,shlex,statistics,sys
import host
HERE=Path(__file__).resolve().parent;run=sys.argv[1] if len(sys.argv)>1 else 'r1'
code=r'''
from pathlib import Path
import json
root=Path(ROOT);state=json.loads((root/'state.json').read_text())
p=Path('/proc',str(state['pid']),'stat');live=p.exists() and p.read_text().rsplit(')',1)[1].split()[0]!='Z'
print(json.dumps({'state':state,'worker_live':live,'logs':{p.stem.removeprefix('capture-'):p.read_text(errors='replace') for p in root.glob('capture-*.log')}}))
'''.replace('ROOT',repr('/var/lib/samurai/k311-joint-'+run))
if '--offline' in sys.argv:data=json.loads((host.PRIVATE/('runtime-'+run+'-results.json')).read_text())
else:
    q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=30)
    (host.PRIVATE/('runtime-'+run+'-results.json')).write_bytes(q.stdout)
    data=json.loads(q.stdout)
if not data['state']['terminal'] or data['worker_live']:raise RuntimeError('Run is live; inspect the same handle')
report={'stage':311,'capture':data['state']['summary'],'sensors':{}}
for model,text in data['logs'].items():
    errors=[];norm=1 if model=='imx319' else 1.06201171875
    quant=lambda x:min((math.floor(x*norm*1024+.5)+4)>>3,4095)/((math.floor(norm*1024+.5)+4)>>3)
    pairs={int(r):(int(s),float(m)) for s,r,m in re.findall(r'Pair epoch=1 sof=(\d+) request=(\d+) population=\d+ mean=([\d.e+-]+)',text)}
    wb={int(r):(float(a),float(b),int(l)) for r,a,b,l in re.findall(r'APPLICATION_WB epoch=0 request=(\d+) red=([\d.e+-]+) blue=([\d.e+-]+) locked=(\d+)',text)}
    mode={int(r):int(enabled) for r,enabled in re.findall(r'APPLICATION_AWB_MODE epoch=0 request=(\d+) enabled=(\d+)',text)}
    queued={int(rev):(float(r),float(b)) for rev,r,b in re.findall(r'WB queue epoch=1 revision=(\d+) red=([\d.e+-]+) blue=([\d.e+-]+)',text)}
    applied=[(int(sof),int(rev),int(mode)) for rev,sof,mode in re.findall(r'ISP applied epoch=1 revision=(\d+) first-sof=(\d+) awb=(\d+)',text)]
    accepted={int(source):int(rev) for source,rev in re.findall(r'WB request epoch=1 source=(\d+) revision=(\d+) awb=-?\d+',text)}
    commands=[(int(source),int(phase)) for source,phase in re.findall(r'APPLICATION_CONTROL epoch=0 request=(\d+) phase=(\d+)',text)]
    rgb={int(r):list(map(float,values.split())) for r,values in re.findall(r'APPLICATION_RGB epoch=0 request=(\d+)((?: [\d.e+-]+){12})',text)}
    rgbSof={pairs[r][0]:values for r,values in rgb.items() if r in pairs}
    effective={};ambiguous=[]
    def possible_quantized(value):
        # The proposal log has six significant digits; rounding can straddle a Q10/Q7 boundary.
        half=0 if not value else .5*10**(math.floor(math.log10(abs(value)))-5)
        a=round(quant(max(0,value-half))*((math.floor(norm*1024+.5)+4)>>3))
        b=round(quant(value+half)*((math.floor(norm*1024+.5)+4)>>3))
        green=(math.floor(norm*1024+.5)+4)>>3
        return [n/green for n in range(a,b+1)]
    for r,(sof,_) in pairs.items():
        eligible=[x for x in applied if x[0]<=sof]
        if not eligible or r not in wb or r not in mode:
            errors.append({'sof':sof,'reason':'missing metadata or confirmation'});continue
        start,revision,enabled=max(eligible)
        wanted=queued.get(revision) if revision else (4,.5)
        possible=[possible_quantized(y) for y in wanted] if wanted else []
        if not wanted or any(not any(abs(x-y)<1e-5 for y in values) for x,values in zip(wb[r][:2],possible)) or mode[r]!=enabled or (not enabled and wb[r][2]):
            errors.append({'sof':sof,'reason':'WB gains/mode mismatch'})
        if any(len(values)>1 for values in possible):ambiguous.append({'sof':sof,'revision':revision})
        effective[sof]=(wb[r][0],wb[r][1],enabled)
    if len(pairs)!=len(wb) or len(pairs)!=len(mode):errors.append('Metadata count differs')
    controls=[];physical=[]
    for source,phase in commands:
        revision=accepted.get(source);ack=next((x for x in applied if x[1]==revision),None)
        if ack is None:errors.append({'source':source,'reason':'request not acknowledged'});continue
        sof,_,enabled=ack
        requestSof=pairs[source][0] if source in pairs else None
        if requestSof is None or sof!=requestSof:errors.append({'source':source,'reason':'WB effect differs from its requested image','first_sof':sof,'request_sof':requestSof})
        controls.append({'request':source,'phase':phase,'revision':revision,'first_sof':sof,'request_sof':requestSof,'enabled':enabled,'queued_gains':queued.get(revision)})
        if phase not in [1,2] or sof-1 not in effective or sof not in effective:continue
        before=effective[sof-1];after=effective[sof]
        if before[:2]==after[:2]:continue
        for band in range(4):
            for channel,name in [(0,'R/G'),(2,'B/G')]:
                samples={s:values[band*3+channel]/values[band*3+1] for s,values in rgbSof.items() if values[band*3+1]>3}
                if any(s not in samples for s in range(sof-3,sof+3)):continue
                pre=statistics.median(samples[s] for s in range(sof-3,sof));post=statistics.median(samples[s] for s in range(sof,sof+3));delta=post-pre
                noise=max(statistics.median(abs(samples[s]-pre) for s in range(sof-3,sof)),statistics.median(abs(samples[s]-post) for s in range(sof,sof+3)),1e-7)
                ratio=after[0 if channel==0 else 1]/before[0 if channel==0 else 1]
                useful=abs(delta)>6*noise and abs(delta)>.02*max(abs(pre),abs(post))
                aligned=useful and (ratio-1)*delta>0 and abs(samples[sof-1]-pre)<.15*abs(delta) and all((samples[s]-pre)/delta>=.15 for s in range(sof,sof+3))
                physical.append({'phase':phase,'first_sof':sof,'band':band,'channel':name,'useful':useful,'first_response_aligned':aligned,
                                 'expected_gain_ratio':ratio,'measured_colour_ratio':post/pre if pre else None})
    phases=[int(p) for p in re.findall(r'APPLICATION_PHASE epoch=0 phase=(\d+) after_request=\d+',text)]
    if phases!=[1,2,3,4]:errors.append('State-driven transition sequence incomplete')
    if [p for _,p in commands]!=[1,2,3]:errors.append('Three request controls not observed')
    if len(controls)==3:
        if [r['enabled'] for r in controls]!=[0,0,1] or controls[0]['queued_gains']!=(1.25,.75) or controls[1]['queued_gains']!=(2.,.5) or controls[2]['queued_gains']!=(2.,.5):errors.append('Manual control or ignored-auto gain semantics differ')
        start,end=controls[0]['first_sof'],controls[2]['first_sof']
        allowed={r['revision'] for r in controls[:2]}
        if any(start<=sof<end and rev not in allowed for sof,rev,_ in applied):errors.append('Unexpected automatic WB update while disabled')
    config=re.findall(r'Sensor configuration model=\S+ pixel-rate=(\d+) line-length=(\d+) frame-length=(\d+)',text)
    sensorContexts={int(s):(int(v),int(x),int(g)) for s,v,x,g in re.findall(r'SensorContext epoch=1 sof=(\d+) valid=(\d+) exposure-lines=(\d+) gain-code=(\d+) source=\d+',text)}
    sensorMeta=[(int(r),int(x),float(g),int(em),int(gm)) for r,x,g,em,gm in re.findall(r'APPLICATION_SENSOR_METADATA epoch=0 request=(\d+) exposure_us=(\d+) analogue_gain=([\d.e+-]+) exposure_mode=(\d+) gain_mode=(\d+)',text)]
    if config:
        rate,line,_=map(int,config[-1])
        for r,t,g,em,gm in sensorMeta:
            if r not in pairs or pairs[r][0] not in sensorContexts:errors.append('Sensor context missing');continue
            valid,lines,code=sensorContexts[pairs[r][0]];wanted=1024/(1024-code) if model in ['imx319','imx471'] else code/32
            if not valid or t!=math.floor(lines*line*1e6/rate+.5) or abs(g-wanted)>5e-6*max(1,wanted) or em!=0 or gm!=0:errors.append('Sensor metadata mismatch during WB changes')
    else:errors.append('Sensor timing not configured')
    report['sensors'][model]={'frames':len(pairs),'controls':controls,'completed_phases':phases,'errors':errors,
        'wb_parameter_updates':len(queued),'ae_proposals':len(re.findall(r'AE update epoch=',text)),
        'manual_frames':sum(v==0 for v in mode.values()),'manual_physical_responses':physical,
        'gain_metadata_unique_quantization_frames':len(pairs)-len(ambiguous),'rounded_proposal_quantization_ambiguous_frames':ambiguous,
        'useful_physical_domains':sum(p['useful'] for p in physical),'aligned_physical_domains':sum(p['first_response_aligned'] for p in physical),
        'final_mean_luma':statistics.mean(list(pairs.values())[-i][1]/1023 for i in range(1,min(8,len(pairs))+1)) if pairs else None}
report['passed']=report['capture']['passed'] and len(report['sensors'])==4 and all(not s['errors'] for s in report['sensors'].values())
report['formal_colour_calibration']=False
(HERE/('runtime-'+run+'-validation.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'passed':report['passed'],'sensors':{m:{k:v for k,v in s.items() if k!='manual_physical_responses'} for m,s in report['sensors'].items()}},indent=2))
