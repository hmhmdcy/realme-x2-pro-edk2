"""Collect the existing runs; check mode timing, WB and joint AE evidence."""
from pathlib import Path
import json,math,re,shlex,statistics,sys
import host
HERE=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import hashlib,json,struct,subprocess
def note(raw):
    offset=struct.unpack_from('<Q',raw,40)[0];size,count,strings=struct.unpack_from('<HHH',raw,58)
    sections=[struct.unpack_from('<IIQQQQIIQQ',raw,offset+i*size) for i in range(count)]
    names=raw[sections[strings][4]:sections[strings][4]+sections[strings][5]]
    return next(raw[x[4]:x[4]+x[5]] for x in sections if names[x[0]:].split(b'\0',1)[0]==b'.note.gnu.build-id')
runs={}
for n in [1,2,3,4]:
    root=Path('/var/lib/samurai/k309-cameras-r'+str(n))
    runs[str(n)]={'state':json.loads((root/'state.json').read_text()),
                  'logs':{p.stem.removeprefix('capture-'):p.read_text(errors='replace') for p in root.glob('capture-*.log')}}
module=Path(subprocess.check_output(['modinfo','-n','qcom_camss'],text=True).strip())
health={'taint':int(Path('/proc/sys/kernel/tainted').read_text()),
        'camss_sha256':hashlib.sha256(module.read_bytes()).hexdigest(),
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
        args=(p/'cmdline').read_bytes().split(b'\0')
        if any(a.startswith(b'/var/lib/samurai/k309-cameras-') and a.rsplit(b'/',1)[-1] in
               [b'camera-smoke',b'camss_ipa_proxy',b'pipeline-fixture'] for a in args):
            health['workers_live'].append(int(p.name))
    except (FileNotFoundError,ProcessLookupError):pass
print(json.dumps({'runs':runs,'health':health}))
'''
if '--offline' in sys.argv:data=json.loads((host.PRIVATE/'capture-results.json').read_text())
else:
    q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=25)
    (host.PRIVATE/'capture-results.json').write_bytes(q.stdout);data=json.loads(q.stdout)
def quantize(value,norm):
    return min((math.floor(value*norm*1024+.5)+4)>>3,4095)/((math.floor(norm*1024+.5)+4)>>3)
report={'stage':309,'runs':{},'health':data['health']}
for n,run in data['runs'].items():
    result={'summary':run['state']['summary'],'cameras':{}}
    for model,text in run['logs'].items():
        norm=1.0 if model=='imx319' else 1.06201171875
        pairs={int(r):int(s) for s,r in re.findall(r'Pair epoch=1 sof=(\d+) request=(\d+)',text)}
        contexts={int(s):int(v) for s,v in re.findall(r'WB context epoch=1 sof=(\d+) revision=(\d+) known=1',text)}
        acks=[(int(s),int(v)) for s,v in re.findall(r'Parameters epoch=1 first-sof=(\d+) revision=(\d+)',text)]
        queued={int(v):(float(r),float(b)) for v,r,b in re.findall(r'WB queue epoch=1 revision=(\d+) red=([\d.e+-]+) blue=([\d.e+-]+)',text)}
        metadata=[];errors=[]
        for request,r,b,locked in re.findall(r'APPLICATION_WB epoch=0 request=(\d+) red=([\d.e+-]+) blue=([\d.e+-]+) locked=(\d+)',text):
            sof=pairs.get(int(request))
            eligible=[(s,v) for s,v in acks if sof is not None and s<=sof]
            if not eligible:errors.append('unpaired frame');continue
            _,revision=max(eligible)
            wanted=queued[revision] if revision else (4.,.5)
            if contexts.get(sof)!=revision or any(abs(x-quantize(y,norm))>1e-5 for x,y in zip([float(r),float(b)],wanted)):
                errors.append({'sof':sof,'revision':revision})
            metadata.append({'sof':sof,'red':float(r),'blue':float(b),'locked':bool(int(locked))})
        timestamps=[int(t) for t in re.findall(r'APPLICATION_FRAME number=\d+ request=\d+ sequence=\d+ timestamp=(\d+)',text)]
        deltas=[(b-a)/1000 for a,b in zip(timestamps,timestamps[1:]) if b>a]
        sensor=[(int(t),float(g)) for t,g in re.findall(r'APPLICATION_SENSOR_METADATA .* exposure_us=(\d+) analogue_gain=([\d.e+-]+)',text)]
        means=[float(m)/1023 for m in re.findall(r'Pair epoch=1 sof=\d+ request=\d+ population=\d+ mean=([\d.e+-]+)',text)]
        configured=re.findall(r'Sensor configuration model=\S+ pixel-rate=(\d+) line-length=(\d+) frame-length=(\d+)',text)
        sensorErrors=[]
        sensorContexts={int(sof):(int(e),int(g)) for sof,e,g in re.findall(
            r'SensorContext epoch=1 sof=(\d+) valid=1 exposure-lines=(\d+) gain-code=(\d+)',text)}
        if configured:
            rate,line,_=map(int,configured[-1])
            for request,t,g in re.findall(r'APPLICATION_SENSOR_METADATA epoch=0 request=(\d+) exposure_us=(\d+) analogue_gain=([\d.e+-]+)',text):
                sof=pairs.get(int(request));context=sensorContexts.get(sof)
                if not context:sensorErrors.append('missing sensor context');continue
                lines,code=context
                wantedGain=1024/(1024-code) if model in ['imx319','imx471'] else code/32
                wantedTime=math.floor(lines*line*1e6/rate+.5)
                if int(t)!=wantedTime or abs(float(g)-wantedGain)>1e-5:sensorErrors.append({'sof':sof,'time':int(t),'gain':float(g)})
        tail=statistics.mean(means[-5:]) if means else None
        result['cameras'][model]={
            'image_frames':len(timestamps),'same_sof_quantized_metadata_errors':errors,
            'sensor_metadata_model_errors':sensorErrors,
            'parameter_updates':len(acks)-1 if acks else 0,'last_wb':metadata[-1] if metadata else None,
            'locked_frames':sum(r['locked'] for r in metadata),
            'median_frame_period_us':round(statistics.median(deltas),3) if deltas else None,
            'configured_array_timing':list(map(int,configured[-1])) if configured else None,
            'ae_proposals':len(re.findall(r'AE update epoch=',text)),
            'sensor_tail':sensor[-5:],'mean_luma_tail':tail,
            'mean_target_0_16_reached':tail is not None and abs(tail-.16)<.012 if run['state']['summary']['automatic_exposure_and_awb'] else None}
    report['runs'][n]=result
health=report['health']
report['resources_restored']=health['taint']==0 and health['loaded_camss_matches_disk'] and all(
    v=='suspended' for v in health['platforms'].values()) and len(health['rails'])==9 and all(
    v=={'state':'disabled','users':0} for v in health['rails'].values()) and health['consumers']=={'pipewire':1,'wireplumber':1} and not health['workers_live']
report['four_camera_on_fixed_module']=data['runs']['3']['state']['summary']['passed']
report['joint_control_run_passed']=all(data['runs'][n]['state']['summary']['passed'] for n in ['2','4'])
report['metadata_passed']=all(not camera['same_sof_quantized_metadata_errors'] and not camera['sensor_metadata_model_errors'] for r in report['runs'].values() for camera in r['cameras'].values())
report['passed']=report['resources_restored'] and report['four_camera_on_fixed_module'] and report['joint_control_run_passed'] and report['metadata_passed']
report['initial_main_clock_rejection_preserved']=data['runs']['1']['state']['summary']['captures']['s5kgw1']['image_frames']==0
(HERE/'capture-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'passed':report['passed'],'resources_restored':report['resources_restored'],
 'runs':{n:{model:{k:r[k] for k in ['image_frames','parameter_updates','median_frame_period_us','ae_proposals','mean_luma_tail','mean_target_0_16_reached']}
            for model,r in run['cameras'].items()} for n,run in report['runs'].items()}},indent=2))
