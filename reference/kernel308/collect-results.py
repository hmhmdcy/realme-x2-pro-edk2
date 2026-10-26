"""Check parameter revisions, same-SOF metadata and observed image response."""
from pathlib import Path
import json,math,re,shlex,statistics,sys
import host
HERE=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,os,struct,subprocess
def note(raw):
    offset=struct.unpack_from('<Q',raw,40)[0];size,count,strings=struct.unpack_from('<HHH',raw,58)
    sections=[struct.unpack_from('<IIQQQQIIQQ',raw,offset+i*size) for i in range(count)]
    names=raw[sections[strings][4]:sections[strings][4]+sections[strings][5]]
    return next(raw[x[4]:x[4]+x[5]] for x in sections if names[x[0]:].split(b'\0',1)[0]==b'.note.gnu.build-id')
runs={}
for n in RUN_NUMBERS:
    root=Path('/var/lib/samurai/k308-awb-r'+str(n))
    runs[str(n)]={'state':json.loads((root/'state.json').read_text()),'log':(root/'capture.log').read_text(errors='replace')}
module=Path(subprocess.check_output(['modinfo','-n','qcom_camss'],text=True).strip())
health={'taint':int(Path('/proc/sys/kernel/tainted').read_text()),
        'loaded_camss_matches_disk':note(module.read_bytes())==Path('/sys/module/qcom_camss/notes/.note.gnu.build-id').read_bytes(),
        'platforms':{n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip()
                     for n in ['acb3000.camss','ac4a000.cci','ac4b000.cci']},'rails':{},'consumers':{},'workers_live':[]}
for p in Path('/sys/class/regulator').glob('regulator.*'):
    name=(p/'name').read_text().strip()
    if name.startswith(('cam-main-','cam-front-','cam-rear-','cam-tele-')):
        health['rails'][name]={'state':(p/'state').read_text().strip(),'users':int((p/'num_users').read_text())}
for p in Path('/proc').glob('[0-9]*'):
    try:
        name=(p/'comm').read_text().strip()
        if name in ['pipewire','wireplumber']:health['consumers'][name]=health['consumers'].get(name,0)+1
        argv=(p/'cmdline').read_bytes().split(b'\0')
        if any(arg.startswith(b'/var/lib/samurai/k308-awb-') and arg.rsplit(b'/',1)[-1] in
               [b'awb-smoke',b'camss_ipa_proxy',b'pipeline-fixture'] for arg in argv):
            health['workers_live'].append(int(p.name))
    except (FileNotFoundError,ProcessLookupError):pass
print(json.dumps({'runs':runs,'health':health}))
'''
offline='--offline' in sys.argv
numbers=list(map(int,[v for v in sys.argv[1:] if v!='--offline'])) if len(sys.argv)>1 and not offline else [1,2,3,4]
code=code.replace('RUN_NUMBERS',repr(numbers))
if offline:
    data=json.loads((host.PRIVATE/'capture-results.json').read_text())
else:
    q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=25)
    (host.PRIVATE/'capture-results.json').write_bytes(q.stdout)
    data=json.loads(q.stdout)
def full_range_means(values):
    # The probe retained unclamped limited-range inverse values. Recover
    # Y/Cb/Cr linearly, then invert the driver's actual full-range BT.601 CST.
    full=[]
    for n in range(0,12,3):
        r,g,b=values[n:n+3]
        a=(g+(.392/2.017)*b+(.813/1.596)*r)/(1+.392/2.017+.813/1.596)
        y=a/1.164+16;u=(b-a)/2.017;v=(r-a)/1.596
        full += [y+1.402*v,y-.344136*u-.714136*v,y+1.772*u]
    return full
def correlate(points):
    if len(points)<8:return None
    xs,ys=zip(*points);mx=statistics.mean(xs);my=statistics.mean(ys)
    vx=sum((x-mx)**2 for x in xs);vy=sum((y-my)**2 for y in ys)
    if vx<1e-5 or vy<1e-5:return None
    return sum((x-mx)*(y-my) for x,y in points)/math.sqrt(vx*vy)
def quantize(value,norm):
    common=math.floor(value*norm*1024+.5)
    green=(math.floor(norm*1024+.5)+4)>>3
    return min((common+4)>>3,4095)/green
report={'stage':308,'runs':{},'health':data['health']}
for n,run in data['runs'].items():
    text=run['log'];norm=1.0 if run['state']['summary']['sensor']=='imx319' else 1.06201171875
    pairs={(int(e),int(r)):int(s) for e,s,r in re.findall(r'Pair epoch=(\d+) sof=(\d+) request=(\d+)',text)}
    contexts={(int(e),int(s)):int(v) for e,s,v in re.findall(r'WB context epoch=(\d+) sof=(\d+) revision=(\d+) known=1',text)}
    acks={}
    for e,s,v in re.findall(r'Parameters epoch=(\d+) first-sof=(\d+) revision=(\d+)',text):
        acks.setdefault(int(e),[]).append((int(s),int(v)))
    queued={(int(e),int(v)):(float(r),float(b)) for e,v,r,b in re.findall(r'WB queue epoch=(\d+) revision=(\d+) red=([\d.e+-]+) blue=([\d.e+-]+)',text)}
    frames={}
    errors=[]
    for e,r,a,b,locked in re.findall(r'APPLICATION_WB epoch=(\d+) request=(\d+) red=([\d.e+-]+) blue=([\d.e+-]+) locked=(\d+)',text):
        epoch=int(e)+1;request=int(r);sof=pairs.get((epoch,request))
        if sof is None:errors.append('missing pair');continue
        eligible=[(s,v) for s,v in acks.get(epoch,[]) if s<=sof]
        if not eligible:errors.append('missing parameter context');continue
        _,revision=max(eligible)
        gains=queued.get((epoch,revision),(4.,.5) if epoch==1 else (.5,4.)) if revision else ((4.,.5) if epoch==1 else (.5,4.))
        actual=(float(a),float(b))
        expected=tuple(quantize(v,norm) for v in gains)
        if contexts.get((epoch,sof))!=revision or any(abs(x-y)>1e-5 for x,y in zip(actual,expected)):
            errors.append({'epoch':epoch,'sof':sof,'revision':revision,'actual':actual,'expected':expected})
        frames[(epoch,sof)]={'request':request,'revision':revision,'gains':actual,'locked':bool(int(locked))}
    for e,r,values in re.findall(r'APPLICATION_RGB epoch=(\d+) request=(\d+)((?: [-\d.e+]+){12})',text):
        epoch=int(e)+1;sof=pairs.get((epoch,int(r)))
        if (epoch,sof) in frames:frames[(epoch,sof)]['pixels']=full_range_means(list(map(float,values.split())))
    epochs=[]
    for epoch in sorted(acks):
        rows=sorted((s,f) for (e,s),f in frames.items() if e==epoch)
        epochs.append({'epoch':epoch,'frames':len(rows),'last_gains':rows[-1][1]['gains'] if rows else [],
                       'locked_frames':sum(f['locked'] for _,f in rows),
                       'parameter_revisions':len(acks[epoch])-1})
    firstUpdateDomains=[]
    for epoch in sorted(acks):
        updates=sorted((s,v) for s,v in acks[epoch] if v)
        if not updates:continue
        firstSof,revision=updates[0]
        sequence=[frames.get((epoch,firstSof+d)) for d in [-2,-1,0,1]]
        if any(not f or 'pixels' not in f for f in sequence):continue
        for band in range(4):
            for channel,index in [(0,0),(2,1)]:
                values=[(f['pixels'][3*band+channel],f['pixels'][3*band+1]) for f in sequence]
                if min(v for pair in values for v in pair)<=3:continue
                ratios=[math.log(a/b) for a,b in values]
                before=ratios[1]-ratios[0];effect=ratios[2]-ratios[1];after=ratios[3]-ratios[2]
                command=math.log(sequence[2]['gains'][index]/sequence[1]['gains'][index])
                useful=abs(effect)>.01 and abs(effect)>5*max(abs(before),abs(after),.001)
                firstUpdateDomains.append({'epoch':epoch,'band':band,'channel':'R' if channel==0 else 'B',
                    'acknowledged_sof':firstSof,'before_delta':round(before,6),'at_ack_delta':round(effect,6),
                    'after_delta':round(after,6),'useful':useful,'direction_matches':effect*command>0})
    domains=[]
    for epoch in sorted(acks):
        for band in range(4):
            for channel,gainIndex in [(0,0),(2,1)]:
                candidates=[]
                for lag in [0,1,2,3]:
                    points=[]
                    for (e,sof),f in frames.items():
                        prev=frames.get((e,sof-1));command=frames.get((e,sof-lag));commandPrev=frames.get((e,sof-lag-1))
                        if e!=epoch or not prev or not command or not commandPrev or 'pixels' not in f or 'pixels' not in prev:continue
                        values=[f['pixels'][band*3+channel],f['pixels'][band*3+1],
                                prev['pixels'][band*3+channel],prev['pixels'][band*3+1]]
                        if min(values)<=3:continue
                        x=math.log(command['gains'][gainIndex]/commandPrev['gains'][gainIndex])
                        y=math.log((values[0]/values[1])/(values[2]/values[3]))
                        points.append((x,y))
                    c=correlate(points)
                    if c is not None:candidates.append({'lag':lag,'correlation':round(c,6),'samples':len(points)})
                if candidates:
                    domains.append({'epoch':epoch,'band':band,'channel':'R' if channel==0 else 'B',
                                    'candidates':candidates,'best':max(candidates,key=lambda c:c['correlation'])})
    summary=run['state'].get('summary',{})
    report['runs'][n]={'summary':summary,'metadata_frames_checked':len(frames),'metadata_errors':errors,
                      'epochs':epochs,'physical_response_domains':domains,
                      'first_update_domains':firstUpdateDomains,
                      'all_physical_updates_uniquely_timed':False,
                      'pixel_transfer':'Unclamped limited inverse recovered to YCbCr, then full-range BT.601 per active CAMSS CST',
                      'physical_correlation_is_not_independent_with_periodic_updates':True,
                      'all_metadata_matches_acknowledged_quantized_parameters':not errors and len(frames)==summary.get('image_frames'),
                      'algorithm_lock_is_not_colour_accuracy_calibration':True}
health=report['health']
report['resources_restored']=health['taint']==0 and health['loaded_camss_matches_disk'] and all(
    x=='suspended' for x in health['platforms'].values()) and len(health['rails'])==9 and all(
    x=={'state':'disabled','users':0} for x in health['rails'].values()) and health['consumers']=={'pipewire':1,'wireplumber':1} and not health['workers_live']
report['passed']=report['resources_restored'] and all(r['summary'].get('passed') and r['all_metadata_matches_acknowledged_quantized_parameters'] for r in report['runs'].values())
report['image_frames']=sum(r['summary']['image_frames'] for r in report['runs'].values())
report['isp_gain_updates']=sum(e['parameter_revisions'] for r in report['runs'].values() for e in r['epochs'])
report['all_epochs_locked']=all(e['locked_frames']>=8 for r in report['runs'].values() for e in r['epochs'])
first=[d for r in report['runs'].values() for d in r['first_update_domains'] if d['useful']]
report['first_update_observable_domains']=len(first)
report['first_update_observable_domains_aligned']=bool(first) and all(d['direction_matches'] and d['acknowledged_sof']==2 for d in first)
(HERE/'awb-capture-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({key:report[key] for key in ['passed','resources_restored','image_frames',
 'isp_gain_updates','all_epochs_locked','first_update_observable_domains','first_update_observable_domains_aligned']},indent=2))
