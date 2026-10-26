"""Capture using CAMSS309; no module switch or desktop restart."""
from pathlib import Path
import hashlib,json,os,re,subprocess,sys,time,traceback
root=Path(sys.argv[1]);kind=sys.argv[2];models=sys.argv[3].split(',')
root.mkdir(mode=0o700)
state={'stage':313,'pid':os.getpid(),'terminal':False,'phase':'preflight'}
def save():
    temp=root/'state-next.json';temp.write_text(json.dumps(state,indent=2)+'\n');temp.replace(root/'state.json')
def consumers():
    result={}
    for p in Path('/proc').glob('[0-9]*'):
        try:
            name=(p/'comm').read_text().strip()
            if name in ['pipewire','wireplumber']:result[name]=int(p.name)
        except FileNotFoundError:pass
    return result
def health():
    return {'taint':int(Path('/proc/sys/kernel/tainted').read_text()),
        'platforms':{name:Path('/sys/bus/platform/devices',name,'power/runtime_status').read_text().strip()
                     for name in ['acb3000.camss','ac4a000.cci','ac4b000.cci']},
        'rails':{(p/'name').read_text().strip():{'state':(p/'state').read_text().strip(),'users':int((p/'num_users').read_text())}
                 for p in Path('/sys/class/regulator').glob('regulator.*')
                 if (p/'name').read_text().startswith(('cam-main-','cam-front-','cam-rear-','cam-tele-'))}}
save();failure=None;captures={}
before=subprocess.check_output(['dmesg']);before_consumers=consumers()
try:
    if Path('/proc/sys/kernel/random/boot_id').read_bytes()!=Path('/var/lib/samurai/k305-geometry-r2/boot-id-private.txt').read_bytes():raise RuntimeError('Device restarted')
    note='19f4c3571053c60ea81004c89c9e570a7532f33e6f23c7fbb00076b176fd1113'
    if hashlib.sha256(Path('/sys/module/qcom_camss/notes/.note.gnu.build-id').read_bytes()).hexdigest()!=note:raise RuntimeError('Different CAMSS is loaded')
    runtime=Path('/var/lib/samurai/k313-runtime')
    tools=Path('/var/lib/samurai/k313-runtime')
    for selection in models:
        model,_,size=selection.partition('@')
        state.update(phase='capturing',sensor=model);save()
        env=dict(os.environ,LD_LIBRARY_PATH=str(runtime/'lib'),CAMSS_SENSOR_MODEL=model,
                 CAMSS_AWB_EPOCHS='1',CAMSS_AE_ENABLE='1' if kind=='joint' else '0',
                 LIBCAMERA_CAMSS_VFE_ENABLE='1',LIBCAMERA_PIPELINES_MATCH_LIST='camss-vfe',
                 LIBCAMERA_CAMSS_VFE_PROFILE=str(tools/'profile'/(model+'.yaml')),
                 LIBCAMERA_IPA_MODULE_PATH=str(runtime/'ipa'),LIBCAMERA_IPA_PROXY_PATH=str(runtime/'proxy'),
                 LIBCAMERA_IPA_FORCE_ISOLATION='1',LIBCAMERA_LOG_LEVELS='*:WARN,CamssVfe:DEBUG,IPACamss:DEBUG,DelayedControls:DEBUG')
        env['CAMSS_SENSOR_SIZE']=size or ('4608x2592' if model=='s5kgw1' else '1928x1088')
        if kind=='joint' or kind.startswith('af-'):
            env.pop('LIBCAMERA_CAMSS_VFE_PROFILE',None)
            env['LIBCAMERA_IPA_CONFIG_PATH']=str(runtime/'profile')
            if os.environ.get('CAMSS_TEST_HOLD_BUFFERS'):env['CAMSS_TEST_HOLD_BUFFERS']='1'
        app=[str(tools/'bin/af-smoke'),kind.removeprefix('af-')]
        label=selection.replace('@','-')
        with (root/('capture-'+label+'.log')).open('xb') as log:
            child=subprocess.Popen([str(runtime/'bin/pipeline-fixture'),'/dev/media0',*app],env=env,
                stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            state['child_pid']=child.pid;save()
            try:ret=child.wait(timeout=62)
            except subprocess.TimeoutExpired:
                import signal
                child.send_signal(signal.SIGINT);ret=child.wait(timeout=10)
        text=(root/('capture-'+label+'.log')).read_text(errors='replace')
        captures[label]={'exit':ret,'image_frames':text.count('AF_IMAGE '),
                         'fixture_restored':'FIXTURE_RESTORATION result=0' in text,
                         'control_writes':text.count('CONTROL_WRITE ')}
        if ret or not captures[label]['fixture_restored']:raise RuntimeError(model+' capture failed')
except BaseException:
    failure=traceback.format_exc();(root/'failure.txt').write_text(failure)
finally:
    for _ in range(30):
        status=health()
        if all(v=='suspended' for v in status['platforms'].values()):break
        time.sleep(.2)
    after=subprocess.check_output(['dmesg'])
    faults={w.decode():after.count(w)-before.count(w) for w in [b'WARNING:',b'Oops:',b'gpu fault:',b'fatal error received',b'CCI error']}
    report={'stage':313,'kind':kind,'deployed_module_reused':True,
            'consumers_unchanged':before_consumers==consumers(),'captures':captures,
            'failure':failure is not None,'fault_delta':faults,'health':status}
    report['passed']=not report['failure'] and report['consumers_unchanged'] and len(captures)==len(models) and all(
        v['exit']==0 and v['fixture_restored'] for v in captures.values()) and not any(faults.values()) and not status['taint'] and all(
        v=='suspended' for v in status['platforms'].values()) and len(status['rails'])==9 and all(v=={'state':'disabled','users':0} for v in status['rails'].values())
    state.update(terminal=True,phase='complete' if report['passed'] else 'failed',summary=report);save()
    print(json.dumps(report))
