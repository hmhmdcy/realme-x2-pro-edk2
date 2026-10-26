from pathlib import Path
import hashlib,host,json,shlex
here=Path(__file__).resolve().parent;proof=json.loads((here/'imx471-module-build-validation.json').read_text());data=(host.PRIVATE/'modules/imx471.ko').read_bytes();assert hashlib.sha256(data).hexdigest()==proof['module_sha256'] and len(data)<65536
stage="from pathlib import Path;import hashlib,sys;p=Path('/var/lib/samurai/k215-baseline/imx471-candidate.ko');assert not p.exists();d=sys.stdin.buffer.read();assert len(d)=="+str(len(data))+" and hashlib.sha256(d).hexdigest()=="+repr(proof['module_sha256'])+";p.write_bytes(d);p.chmod(0o600)"
host.ssh('python3 -c '+shlex.quote(stage),input=data,timeout=30)
code=r'''
from pathlib import Path
import hashlib,json,os,pwd,shutil,signal,subprocess,time
os.umask(0o077);root=Path('/var/lib/samurai');base=root/'k215-baseline';out=root/'k215-driver-test';out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(base/'boot-id-private.txt').read_bytes() and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert Path('/lib/apk/db/installed').read_bytes()==(base/'installed-before-private.txt').read_bytes()
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
tree=Path('/usr/lib/modules')/os.uname().release;target=tree/'kernel/drivers/media/i2c/imx471.ko';candidate=base/'imx471-candidate.ko'
assert sha(target)==sha(base/'imx471-original.ko')=='a28dd67a03afa9e918f87b85030f0158edecbcc2e3f1ce0a36405b78be70ba6a' and sha(candidate)==__HASH__
before_inventory={str(p.relative_to(tree)):sha(p) for p in tree.rglob('*') if p.is_file()};assert len(before_inventory)==786
(out/'module-inventory-before-private.json').write_text(json.dumps(before_inventory,indent=2)+'\n')
for p in [target,*[p for p in tree.iterdir() if p.is_file()]]:
    saved=out/'before-tree'/p.relative_to(tree);saved.parent.mkdir(parents=True,exist_ok=True,mode=0o700);shutil.copyfile(p,saved)
def processes(name):
    found=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            if (p/'comm').read_text().strip()==name and int((p/'status').read_text().split('Uid:',1)[1].split()[0])==10000:found.append(p)
        except OSError:pass
    return found
old=processes('wireplumber');assert len(old)==1;old=old[0]
preserved={name:{p.name:(p/'stat').read_text().split(') ',1)[1].split()[19] for p in processes(name)} for name in ['pipewire','phosh','phoc','gnome-session-b']};assert all(len(v)==1 for v in preserved.values())
assert all(p.read_text().strip()=='closed' for p in Path('/proc/asound').glob('card*/pcm*/sub*/status'))
devices=['/sys/bus/i2c/devices/7-0010','/sys/bus/platform/devices/acb3000.camss','/sys/bus/platform/devices/ac4b000.cci'];assert all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in devices)
argv=[p.decode() for p in (old/'cmdline').read_bytes().split(b'\0') if p];assert argv==['/usr/bin/wireplumber']
env={k.decode():v.decode() for entry in (old/'environ').read_bytes().split(b'\0') if b'=' in entry for k,v in [entry.split(b'=',1)]};assert 'DBUS_SESSION_BUS_ADDRESS' in env and 'XDG_RUNTIME_DIR' in env
(out/'policy-context-private.json').write_text(json.dumps(dict(argv=argv,env=env,old_pid=int(old.name)),indent=2)+'\n')
before=subprocess.check_output(['dmesg']);(out/'dmesg-before-private.txt').write_bytes(before)
state=dict(state='policy-stop-submitted');marker=out/'transition-state-private.json';marker.write_text(json.dumps(state)+'\n')
os.kill(int(old.name),signal.SIGTERM)
for _ in range(50):
    if not old.exists():break
    time.sleep(0.1)
assert not old.exists()
unloaded=False;installed=False;failure=None;restored_old=False
try:
    holders=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            for fd in (p/'fd').iterdir():
                try:destination=os.readlink(fd)
                except OSError:continue
                if destination.startswith(('/dev/media','/dev/v4l-subdev','/dev/video')):holders.append(dict(pid=int(p.name),comm=(p/'comm').read_text().strip(),target=destination))
        except OSError:pass
    (out/'camera-fd-holders-private.json').write_text(json.dumps(holders,indent=2)+'\n');assert not holders
    state['state']='unload-submitted';marker.write_text(json.dumps(state)+'\n')
    p=subprocess.run(['modprobe','-r','imx471'],capture_output=True,timeout=20);(out/'unload-private.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0
    unloaded=True;assert not Path('/sys/module/imx471').exists();state['state']='unloaded';marker.write_text(json.dumps(state)+'\n')
    temporary=target.with_name('imx471.ko.k215-new');assert not temporary.exists();shutil.copyfile(candidate,temporary);temporary.chmod(0o644);os.replace(temporary,target);installed=True
    p=subprocess.run(['depmod','-a'],capture_output=True,timeout=30);(out/'depmod-private.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0
    assert subprocess.check_output(['modinfo','-F','vermagic','imx471'],text=True).strip()==__VERMAGIC__
    state['state']='load-submitted';marker.write_text(json.dumps(state)+'\n')
    p=subprocess.run(['modprobe','imx471'],capture_output=True,timeout=20);(out/'load-private.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0 and Path('/sys/module/imx471').exists()
    assert Path('/sys/bus/i2c/devices/7-0010/driver').resolve().name=='imx471'
    state['state']='new-driver-bound';marker.write_text(json.dumps(state)+'\n')
except Exception as error:
    failure=repr(error);(out/'failure-private.txt').write_text(failure)
    if unloaded and not Path('/sys/module/imx471').exists():
        if installed:shutil.copyfile(base/'imx471-original.ko',target);target.chmod(0o644);subprocess.run(['depmod','-a'],capture_output=True,check=True,timeout=30)
        subprocess.run(['modprobe','imx471'],capture_output=True,check=True,timeout=20);restored_old=True
finally:
    assert len(processes('wireplumber'))==0
    user=pwd.getpwuid(10000)
    def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
    with (out/'policy-restart-private.log').open('wb') as log:child=subprocess.Popen(argv,preexec_fn=demote,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    time.sleep(2);assert child.poll() is None and len(processes('wireplumber'))==1
for name,identities in preserved.items():assert {p.name:(p/'stat').read_text().split(') ',1)[1].split()[19] for p in processes(name)}==identities
after_inventory={str(p.relative_to(tree)):sha(p) for p in tree.rglob('*') if p.is_file()};assert set(after_inventory)==set(before_inventory)
changed=[name for name in after_inventory if name.endswith('.ko') and after_inventory[name]!=before_inventory[name]]
assert changed==(['kernel/drivers/media/i2c/imx471.ko'] if not failure else [])
(out/'module-inventory-after-private.json').write_text(json.dumps(after_inventory,indent=2)+'\n')
after=subprocess.check_output(['dmesg']);(out/'dmesg-after-private.txt').write_bytes(after)
faults={k:after.count(v)-before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()}
report=dict(stage=215,new_sensor_module_installed=not failure,new_module_unload_reload_and_static_bind_verified=not failure,old_module_restored_on_failure=restored_old,transition_failure=failure is not None,only_sensor_ko_changed=not failure,other_771_modules_preserved=True,desktop_and_pipewire_identities_preserved=True,wireplumber_restarted=True,camera_devices_suspended=all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in devices),taint=int(Path('/proc/sys/kernel/tainted').read_text()),fault_delta=faults,no_flash_or_reboot=True,physical_test_pattern_validation_pending=True)
state['state']='verified' if not failure else 'failed-restored';marker.write_text(json.dumps(state)+'\n');(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''.replace('__HASH__',repr(proof['module_sha256'])).replace('__VERMAGIC__',repr(proof['vermagic']))
p=host.ssh('python3 -',input=code.encode(),timeout=130);(host.PRIVATE/'module-reload-host-private.log').write_bytes(p.stdout+p.stderr);report=json.loads(p.stdout);(here/'module-reload-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
