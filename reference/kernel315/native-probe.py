"""Temporarily load the new CAMSS, capture RGB, then restore the deployed module."""
from pathlib import Path
import json, os, pwd, select, signal, subprocess, sys, time, traceback

root = Path(sys.argv[1])
models=sys.argv[2].split(',') if len(sys.argv)>2 else ['imx319']
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
            if (p/'comm').read_text().strip()==name:
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
changed=False
consumers={}
failure=None
save('preflight')
before=subprocess.check_output(['dmesg'])
try:
    if Path('/proc/sys/kernel/random/boot_id').read_bytes()!=Path('/var/lib/samurai/k305-geometry-r2/boot-id-private.txt').read_bytes():
        raise RuntimeError('Device restarted; inspect current state')
    if Path('/proc/sys/kernel/tainted').read_text().strip()!='0': raise RuntimeError('Unexpected taint')
    consumers=services()
    deployed=subprocess.check_output(['modinfo','-n','qcom_camss'],text=True).strip()
    vermagic=subprocess.check_output(['modinfo','-F','vermagic',deployed],text=True).strip()
    candidate=subprocess.check_output(['modinfo','-F','vermagic',str(root/'qcom-camss.ko')],text=True).strip()
    if candidate!=vermagic: raise RuntimeError('Module/kernel mismatch')
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
    save('unloading-deployed')
    run(['rmmod','qcom_camss'],'unload-deployed')
    changed=True
    save('loading-candidate')
    run(['insmod',str(root/'qcom-camss.ko')],'load-candidate')
    run(['cam','-l'],'enumeration')
    save('capturing')
    for selection in models:
        model,kind=selection.split(':')
        env=dict(os.environ,LD_LIBRARY_PATH=str(root/'lib'),
                 LIBCAMERA_CAMSS_VFE_ENABLE='1',LIBCAMERA_PIPELINES_MATCH_LIST='camss-vfe',
                 LIBCAMERA_IPA_MODULE_PATH=str(root/'ipa'),LIBCAMERA_IPA_PROXY_PATH=str(root/'proxy'),
                 LIBCAMERA_IPA_CONFIG_PATH=str(root/'profile'),LIBCAMERA_IPA_FORCE_ISOLATION='1',
                 LIBCAMERA_LOG_LEVELS='*:WARN,CamssVfe:DEBUG,IPACamss:DEBUG')
        label=selection.replace(':','-')
        save('capturing',selection=selection)
        with (root/('capture-'+label+'.log')).open('xb') as log:
            child=subprocess.Popen([str(root/'pipeline-fixture'),'/dev/media0',str(root/'bin/raw-smoke'),model,kind],
                  env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            save('capturing',selection=selection,child_pid=child.pid)
            try:ret=child.wait(timeout=55 if kind.startswith('af') else 24)
            except subprocess.TimeoutExpired:
                child.send_signal(signal.SIGINT);ret=child.wait(timeout=10)
        text=(root/('capture-'+label+'.log')).read_text(errors='replace')
        if ret or 'RAW_RESULT ' not in text or 'FIXTURE_RESTORATION result=0' not in text:raise RuntimeError(selection+' capture failed')

except BaseException:
    failure=traceback.format_exc()
    (root/'failure.txt').write_text(failure)
finally:
    save('restoring-deployment')
    restored=False
    try:
        wait_idle()
        if changed:
            if Path('/sys/module/qcom_camss').exists():
                run(['rmmod','qcom_camss'],'unload-candidate')
            run(['modprobe','qcom_camss'],'restore-deployed')
        restored=True
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
    report=dict(stage=315,failure=failure is not None,deployment_restored=restored,
     captures={m:{'frames':t.count('RAW_IMAGE '),'probe_passed':'RAW_RESULT ' in t and 'failed=0 result=0' in t,'fixture_restored':'FIXTURE_RESTORATION result=0' in t} for m,t in captures.items()},
     fault_delta=faults,taint=int(Path('/proc/sys/kernel/tainted').read_text()),health=health,
     temporary_module_only=True,installed_files_unchanged=True)
    report['passed']=not report['failure'] and restored and all(c['probe_passed'] and c['fixture_restored'] for c in report['captures'].values()) and not any(faults.values()) and not report['taint'] and all(v=='suspended' for v in health['platforms'].values()) and all(v=={'state':'disabled','users':0} for v in health['rails'].values())
    save('complete' if report['passed'] else 'failed',terminal=True,summary=report)
    print(json.dumps(report))
