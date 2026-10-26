"""Temporarily load the new CAMSS, capture RGB, then restore the deployed module."""
from pathlib import Path
import json, os, pwd, re, select, signal, subprocess, sys, time, traceback

root = Path(sys.argv[1])
models=sys.argv[2].split(',')
automatic=sys.argv[3]=='joint'
if not models or not set(models)<={'s5kgw1','imx471','imx319','s5k3m5'}:raise ValueError('camera')
captures={}
verify_raw=len(sys.argv)>4 and sys.argv[4]=='raw'
raw_captures={}
state = {'terminal':False, 'phase':'preflight', 'pid':os.getpid()}
marker = root/'state.json'
if marker.exists():
    raise RuntimeError('Run already exists; inspect it instead of replaying')
def save(phase, **values):
    state.update(phase=phase, **values)
    marker.write_text(json.dumps(state, indent=2)+'\n')
def run(args, label, timeout=20, env=None):
    q=subprocess.run(args, capture_output=True, timeout=timeout, env=env)
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
    for p in Path('/proc/asound').glob('card*/pcm*/sub*/status'):
        if p.read_text().strip()!='closed': raise RuntimeError('Audio is in use')
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
    stage=root/'bundle'
    for model in models:
        save('capturing',sensor=model)
        env=dict(os.environ,LD_LIBRARY_PATH=str(stage/'lib'),CAMSS_AWB_EPOCHS='1',
                 CAMSS_AE_ENABLE='1' if automatic else '0',LIBCAMERA_CAMSS_VFE_ENABLE='1',
                 LIBCAMERA_PIPELINES_MATCH_LIST='camss-vfe',
                 LIBCAMERA_CAMSS_VFE_PROFILE=str(stage/'profile'/(model+'.yaml')),
                 LIBCAMERA_IPA_MODULE_PATH=str(stage/'ipa'),LIBCAMERA_IPA_PROXY_PATH=str(stage/'proxy'),
                 LIBCAMERA_IPA_FORCE_ISOLATION='1',
                 LIBCAMERA_LOG_LEVELS='*:WARN,CamssVfe:DEBUG,IPACamss:DEBUG,IPAManager:DEBUG,IPAProxy:DEBUG')
        label='capture-'+model
        try:
            run([str(stage/'bin/pipeline-fixture'),'/dev/media0',str(stage/'bin/camera-smoke'),model],
                label,timeout=62,env=env)
            captures[model]=0
        except RuntimeError:
            captures[model]=1
            text=(root/(label+'.log')).read_text(errors='replace')
            if 'FIXTURE_RESTORATION result=0' not in text:raise
        wait_idle()
        if verify_raw:
            devices=[p for p in Path('/sys/bus/i2c/drivers',model).iterdir()
                     if p.is_symlink() and re.fullmatch(r'\d+-[0-9a-f]{4}',p.name)]
            if len(devices)!=1:raise RuntimeError('Missing sensor device')
            camera_id='/base'+str((devices[0]/'of_node').resolve()).split('/base',1)[1]
            raw_env=dict(os.environ,LIBCAMERA_PIPELINES_MATCH_LIST='simple',
                         LIBCAMERA_SOFTISP_USE_GPU='0',LIBCAMERA_LOG_LEVELS='*:WARN')
            run([str(stage/'bin/pipeline-fixture'),'/dev/media0','/usr/sbin/cam',
                 '-c',camera_id,'--capture=4'],'raw-'+model,timeout=62,env=raw_env)
            raw_text=(root/('raw-'+model+'.log')).read_text(errors='replace')
            raw_captures[model]={'frames':len(re.findall(r'seq:\s*\d+',raw_text)),
                                 'fixture_restored':'FIXTURE_RESTORATION result=0' in raw_text}
            wait_idle()
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
            for word in [b'WARNING:',b'Oops:',b'gpu fault:',b'fatal error received',b'CCI error']}
    summaries={}
    for model in models:
        p=root/('capture-'+model+'.log')
        text=p.read_text(errors='replace') if p.exists() else ''
        epochs=[dict(epoch=int(e),frames=int(f),failed=int(x),stop=int(y))
                for e,f,x,y in re.findall(r'APPLICATION_EPOCH epoch=(\d+) frames=(\d+) failed=(\d+) stop=(-?\d+)',text)]
        summaries[model]={'exit':captures.get(model),'image_frames':text.count('APPLICATION_FRAME '),
                         'epochs':epochs,'fixture_restored':'FIXTURE_RESTORATION result=0' in text,
                         'isolation_forced':'forced through configuration' in text,
                         'locked_frames':len(re.findall(r'APPLICATION_WB .* locked=1',text))}
    report={'stage':309,'automatic_exposure_and_awb':automatic,'failure':failure is not None,
            'deployment_restored':restored,'captures':summaries,'fault_delta':faults,
            'taint':int(Path('/proc/sys/kernel/tainted').read_text()),
            'temporary_module_only':True,'installed_files_unchanged':True,'raw_captures':raw_captures}
    report['passed']=not report['failure'] and restored and not any(faults.values()) and not report['taint'] and all(
        r['exit']==0 and r['fixture_restored'] and len(r['epochs'])==1 and not r['epochs'][0]['failed']
        for r in summaries.values())
    if verify_raw:report['passed']=report['passed'] and len(raw_captures)==len(models) and all(
        r['frames']==4 and r['fixture_restored'] for r in raw_captures.values())
    save('complete' if report['passed'] else 'failed',terminal=True,summary=report)
    print(json.dumps(report))
