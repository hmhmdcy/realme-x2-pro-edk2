"""Scoped, reversible module parameter experiment; no module file changes."""
from pathlib import Path
import hashlib,json,os,pwd,signal,subprocess,sys,time

root=Path('/var/lib/samurai');out=root/'k219-full-mode-experiment'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k219-runtime/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#183 ')
module=Path('/usr/lib/modules')/os.uname().release/'kernel/drivers/media/i2c/imx471.ko'
assert hashlib.sha256(module.read_bytes()).hexdigest()=='e49dab26b05a325df8da64bb5c4b57c29cd51d1dcf15f5d4ed4dcb53033e66f1'
parameter=Path('/sys/module/imx471/parameters/unprocessed_fullres')
def policies():
    found=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            if (p/'comm').read_text().strip()=='wireplumber' and int((p/'status').read_text().split('Uid:',1)[1].split()[0])==10000:found.append(p)
        except OSError:pass
    return found
def idle():
    assert Path('/sys/bus/i2c/devices/7-0010/power/runtime_status').read_text().strip()=='suspended'
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            for fd in (p/'fd').iterdir():
                try:assert not os.readlink(fd).startswith(('/dev/media','/dev/video','/dev/v4l-subdev'))
                except OSError:pass
        except OSError:pass
def switch(enabled):
    idle()
    Path('/sys/bus/i2c/drivers/imx471/unbind').write_text('7-0010')
    assert not Path('/sys/bus/i2c/devices/7-0010/driver').is_symlink()
    subprocess.run(['modprobe','-r','imx471'],capture_output=True,check=True,timeout=20)
    subprocess.run(['modprobe','imx471','unprocessed_fullres='+str(int(enabled))],capture_output=True,check=True,timeout=20)
    assert Path('/sys/bus/i2c/devices/7-0010/driver').resolve().name=='imx471'
    assert parameter.read_text().strip()==('Y' if enabled else 'N')
    paths=['/sys/bus/i2c/devices/7-0010','/sys/bus/platform/devices/acb3000.camss','/sys/bus/platform/devices/ac4b000.cci']
    deadline=time.monotonic()+5
    while not all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in paths) and time.monotonic()<deadline:time.sleep(0.1)
    assert all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in paths)
def restore_policy():
    context=json.loads((out/'policy-context-private.json').read_text());assert not policies()
    user=pwd.getpwuid(10000)
    def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
    with (out/'policy-restart-private.log').open('ab') as log:
        process=subprocess.Popen(context['argv'],env=context['env'],preexec_fn=demote,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    time.sleep(2);assert process.poll() is None and len(policies())==1
    return process.pid
assert sys.argv[1:] in [['start'],['finish']]
if sys.argv[1]=='start':
    assert not out.exists();out.mkdir(mode=0o700)
    assert parameter.read_text().strip()=='N' and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
    old=policies();assert len(old)==1;old=old[0]
    context=dict(argv=[x.decode() for x in (old/'cmdline').read_bytes().split(b'\0') if x],env={k.decode():v.decode() for e in (old/'environ').read_bytes().split(b'\0') if b'=' in e for k,v in [e.split(b'=',1)]},pid=int(old.name))
    assert context['argv']==['/usr/bin/wireplumber']
    (out/'policy-context-private.json').write_text(json.dumps(context,indent=2)+'\n')
    (out/'state-private.json').write_text(json.dumps(dict(state='policy-stop-submitted'))+'\n')
    os.kill(int(old.name),signal.SIGTERM)
    for _ in range(50):
        if not old.exists():break
        time.sleep(0.1)
    assert not old.exists() and not policies()
    try:switch(True)
    except Exception:
        if Path('/sys/bus/i2c/devices/7-0010/driver').is_symlink():
            if parameter.read_text().strip()!='N':switch(False)
        else:
            if Path('/sys/module/imx471').exists():subprocess.run(['modprobe','-r','imx471'],capture_output=True,check=True,timeout=20)
            subprocess.run(['modprobe','imx471','unprocessed_fullres=0'],capture_output=True,check=True,timeout=20)
        restore_policy();(out/'state-private.json').write_text(json.dumps(dict(state='start-failed-restored'))+'\n');raise
    (out/'state-private.json').write_text(json.dumps(dict(state='full-raw-enabled-policy-paused'))+'\n')
    print(json.dumps(dict(stage=219,experimental_full_raw_enabled=True,policy_paused=True,module_file_unchanged=True)))
else:
    assert json.loads((out/'state-private.json').read_text())['state']=='full-raw-enabled-policy-paused'
    assert not policies();switch(False);new_pid=restore_policy()
    report=dict(stage=219,experimental_full_raw_disabled=True,policy_restored=True,module_file_unchanged=True,taint=int(Path('/proc/sys/kernel/tainted').read_text()))
    (out/'finish-summary.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'state-private.json').write_text(json.dumps(dict(state='finished-default-mode-restored',new_policy_pid=new_pid))+'\n')
    print(json.dumps(report))
