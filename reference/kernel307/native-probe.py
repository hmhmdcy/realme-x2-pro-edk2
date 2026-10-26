"""Temporarily load the new CAMSS, capture RGB, then restore the deployed module."""
from pathlib import Path
import json, os, pwd, select, signal, subprocess, sys, time, traceback

root = Path(sys.argv[1])
tele=len(sys.argv)>2 and sys.argv[2]=='tele'
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
    save('capturing')
    run([str(root/'pipeline-fixture'),'/dev/media0',str(root/'rgb-probe'),'--scene',
         str(root/'frame'), *(['2048','1536','3840'] if tele else ['2273','1946','4096'])],
        'capture',timeout=25)
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
    text=(root/'capture.log').read_text(errors='replace') if (root/'capture.log').exists() else ''
    report=dict(stage=307,sensor='s5k3m5' if tele else 'imx319',failure=failure is not None,deployment_restored=restored,
                rgb_frames=text.count('RGB_BG '),image_frames=text.count('FRAME number='),
                fixture_restored='FIXTURE_RESTORATION result=0' in text,
                fault_delta=faults,taint=int(Path('/proc/sys/kernel/tainted').read_text()),
                temporary_module_only=True,installed_files_unchanged=True)
    report['passed']=not report['failure'] and restored and report['rgb_frames']==36 and report['fixture_restored'] and not any(faults.values()) and not report['taint']
    save('complete' if report['passed'] else 'failed',terminal=True,summary=report)
    print(json.dumps(report))
