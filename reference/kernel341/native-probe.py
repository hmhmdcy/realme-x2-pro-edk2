"""Temporarily run candidate core/IPA on installed CAMSS338, then restore consumers."""
from pathlib import Path
import hashlib, json, os, pwd, select, signal, subprocess, sys, time, traceback

root = Path(sys.argv[1])
cases=json.loads((root/'cases.json').read_text());models=list(cases)
state = {'terminal':False, 'phase':'preflight', 'pid':os.getpid()}
marker = root/'state.json'
if marker.exists():
    raise RuntimeError('Run already exists; inspect it instead of replaying')
def save(phase, **values):
    state.update(phase=phase, **values)
    marker.write_text(json.dumps(state, indent=2)+'\n')
def run(args, label, timeout=20):
    q=subprocess.run(args, capture_output=True, timeout=timeout)
    (root/(label+'.log')).write_bytes(q.stdout+q.stderr)
    if q.returncode: raise RuntimeError(label+' failed')
    return q
def processes(name):
    found=[]
    for p in Path('/proc').glob('[0-9]*'):
        try:
            if (p/'comm').read_text().strip()==name and (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z':
                found.append(p)
        except (FileNotFoundError,ProcessLookupError):pass
    return found
def services():
    result={}
    for name in ['pipewire','wireplumber']:
        ps=processes(name)
        if len(ps)!=1: raise RuntimeError('Expected one '+name+' consumer')
        p=ps[0]
        env=dict(x.decode().split('=',1) for x in (p/'environ').read_bytes().split(b'\0') if x)
        result[name]=dict(pid=int(p.name), uid=p.stat().st_uid,
                          argv=[x.decode() for x in (p/'cmdline').read_bytes().split(b'\0') if x],
                          cwd=os.readlink(p/'cwd'), env=env)
    return result
def wait_idle():
    for _ in range(30):
        if Path('/sys/bus/platform/devices/acb3000.camss/power/runtime_status').read_text().strip()=='suspended':
            return
        time.sleep(.2)
    raise RuntimeError('CAMSS did not suspend')
stopped=[]
consumers={}
failure=None
save('preflight')
before=subprocess.check_output(['dmesg'])
before_note=hashlib.sha256(Path('/sys/module/qcom_camss/notes/.note.gnu.build-id').read_bytes()).hexdigest()
try:
    if Path('/proc/sys/kernel/random/boot_id').read_bytes()!=Path('/var/lib/samurai/k305-geometry-r2/boot-id-private.txt').read_bytes():
        raise RuntimeError('Device restarted; inspect current state')
    if Path('/proc/sys/kernel/tainted').read_text().strip()!='0': raise RuntimeError('Unexpected taint')
    consumers=services()
    if before_note!='0227d29bb5129e2fc69866529147b21b902d441c855f848fd5eaa3093c590297':raise RuntimeError('Expected installed CAMSS338')
    wait_idle()
    save('stopping-consumers')
    for name in ['wireplumber','pipewire']:
        fd=os.pidfd_open(consumers[name]['pid'])
        try:
            signal.pidfd_send_signal(fd,signal.SIGTERM)
            if not select.select([fd],[],[],8)[0]: raise RuntimeError(name+' did not exit')
        finally:os.close(fd)
        stopped.append(name)
    wait_idle()
    save('capturing')
    for selection in models:
        save('capturing',selection=selection)
        item=cases[selection];model=item['model']
        devices=[p for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().startswith(model+' ')]
        if len(devices)!=1:raise RuntimeError('Sensor node not unique: '+model)
        sensor='/dev/'+devices[0].name
        env=dict(os.environ,LIBCAMERA_CAMSS_VFE_PROFILE=str(root/'profiles'/(item['profile']+'.yaml')),LIBCAMERA_LOG_LEVELS='*:INFO,CamssVfe:DEBUG,IPACamss:DEBUG')
        for key in ['LIBCAMERA_CAMSS_VFE_ENABLE','LIBCAMERA_PIPELINES_MATCH_LIST','LIBCAMERA_IPA_FORCE_ISOLATION']:env.pop(key,None)
        env['LIBCAMERA_IPA_MODULE_PATH']=str(root/'ipa');env['LD_LIBRARY_PATH']=str(root/'lib')
        app=[str(root/'pipeline-fixture'),'/dev/media0',str(root/'bin/lsc-aec-smoke'),model,sensor,str(root/selection),item['output'],item['sensor_size'],str(item['test_pattern']),str(root/'profiles'/(item['profile']+'-phase-oracle-private.bin'))]
        with (root/('capture-'+selection+'.log')).open('xb') as log:
            child=subprocess.Popen(app,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            save('capturing',selection=selection,child_pid=child.pid)
            try:ret=child.wait(timeout=40)
            except subprocess.TimeoutExpired:
                child.send_signal(signal.SIGINT);ret=child.wait(timeout=10)
        text=(root/('capture-'+selection+'.log')).read_text(errors='replace')
        expected=' failed=0 result=0'
        if 'FIXTURE_RESTORATION result=0' not in text:raise RuntimeError(selection+' restoration failed')
        if ret or expected not in text:state.setdefault('capture_failures',{})[selection]='Capture incomplete; completed phases retained'

except BaseException:
    failure=traceback.format_exc()
    (root/'failure.txt').write_text(failure)
finally:
    save('restoring-deployment')
    restored=False
    try:
        wait_idle()
        restored=hashlib.sha256(Path('/sys/module/qcom_camss/notes/.note.gnu.build-id').read_bytes()).hexdigest()==before_note
        if not restored:raise RuntimeError('Restored module differs')
    except BaseException:
        (root/'restore-failure.txt').write_text(traceback.format_exc())
    if restored:
        for name in ['pipewire','wireplumber']:
            if name not in stopped:continue
            item=consumers[name]; user=pwd.getpwuid(item['uid'])
            def demote():
                os.initgroups(user.pw_name,user.pw_gid)
                os.setgid(user.pw_gid); os.setuid(user.pw_uid)
            env=item['env'].copy();env.pop('PIPEWIRE_NOTIFICATION_FD',None)
            with (root/(name+'-restart.log')).open('wb') as log:
                child=subprocess.Popen(item['argv'],env=env,cwd=item['cwd'],
                    preexec_fn=demote,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
                    start_new_session=True)
            time.sleep(.5)
            if child.poll() is not None: restored=False
    after=subprocess.check_output(['dmesg'])
    (root/'dmesg-after.txt').write_bytes(after)
    faults={word.decode():after.count(word)-before.count(word)
            for word in [b'WARNING:',b'Oops:',b'gpu fault:',b'fatal error received',b'CCI error',b'Stream stop failed:',b'Failed to disable stream on remote pad:',b'Missing SOF tag',b'Received wm done for unmapped index',b'Unhandled context fault']}
    captures={model:(root/('capture-'+model.replace(':','-')+'.log')).read_text(errors='replace') if (root/('capture-'+model.replace(':','-')+'.log')).exists() else '' for model in models}
    for _ in range(30):
        if all(Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip()=='suspended' for n in ['acb3000.camss','ac4a000.cci','ac4b000.cci']):break
        time.sleep(.2)
    health={'platforms':{n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip() for n in ['acb3000.camss','ac4a000.cci','ac4b000.cci']},
     'rails':{(p/'name').read_text().strip():{'state':(p/'state').read_text().strip(),'users':int((p/'num_users').read_text())} for p in Path('/sys/class/regulator').glob('regulator.*') if (p/'name').read_text().startswith(('cam-main-','cam-front-','cam-rear-','cam-tele-'))}}
    report=dict(stage=341,failure=failure is not None or bool(state.get('capture_failures')),deployment_restored=restored,
     captures={m:{'frames':t.count('CCM_FRAME '),
       'probe_passed':(' failed=0 result=0' in t),
       'settled_phases':t.count('settled=1'),
       'cleanup_restored':('FIXTURE_RESTORATION result=0' in t)} for m,t in captures.items()},
     fault_delta=faults,taint=int(Path('/proc/sys/kernel/tainted').read_text()),health=health,
     temporary_userspace_only=True,installed_camss338_reused=True,installed_files_unchanged=True)
    report['passed']=not report['failure'] and restored and all(c['probe_passed'] and c['cleanup_restored'] for c in report['captures'].values()) and not any(faults.values()) and not report['taint'] and all(v=='suspended' for v in health['platforms'].values()) and all(v=={'state':'disabled','users':0} for v in health['rails'].values())
    save('complete' if report['passed'] else 'failed',terminal=True,summary=report)
    print(json.dumps(report))
