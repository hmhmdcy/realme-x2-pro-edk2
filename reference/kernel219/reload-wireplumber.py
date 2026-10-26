"""Reload the existing idle user policy process without restarting the desktop."""
from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
assert json.loads((here/'r6-package-install-validation.json').read_text())['transaction_state']=='verified'
code=r'''
from pathlib import Path
import hashlib,json,os,pwd,signal,subprocess,time
os.umask(0o077);base=Path('/var/lib/samurai/k219-runtime');out=Path('/var/lib/samurai/k219-r6-package-transaction')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(base/'boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
marker=out/'policy-reload-state-private.json';assert not marker.exists()
def processes(name):
    found=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            if (p/'comm').read_text().strip()==name and int((p/'status').read_text().split('Uid:',1)[1].split()[0])==10000:found.append(p)
        except OSError:pass
    return found
old=processes('wireplumber');assert len(old)==1;old=old[0]
preserved={name:{p.name:(p/'stat').read_text().split(') ',1)[1].split()[19] for p in processes(name)} for name in ['pipewire','phosh','phoc','gnome-session-b']}
assert all(len(v)==1 for v in preserved.values())
pcms={str(p):p.read_text().strip() for p in Path('/proc/asound').glob('card*/pcm*/sub*/status')};assert pcms and all(text=='closed' for text in pcms.values())
argv=[item.decode() for item in (old/'cmdline').read_bytes().split(b'\0') if item];assert argv==['/usr/bin/wireplumber']
assert os.readlink(old/'exe')=='/usr/bin/wireplumber'
env={k.decode():v.decode() for item in (old/'environ').read_bytes().split(b'\0') if b'=' in item for k,v in [item.split(b'=',1)]}
assert 'XDG_RUNTIME_DIR' in env and 'DBUS_SESSION_BUS_ADDRESS' in env
assert not any(k in env for k in ['LD_LIBRARY_PATH','LIBCAMERA_IPA_MODULE_PATH','LIBCAMERA_IPA_PROXY_PATH','LIBCAMERA_IPA_CONFIG_PATH'])
old_maps=(old/'maps').read_text();assert 'libcamera.so' in old_maps
(out/'policy-before-environment-private.json').write_text(json.dumps(dict(pid=int(old.name),argv=argv,environment=env,stat=(old/'stat').read_text(),maps=old_maps),indent=2)+'\n')
before=subprocess.check_output(['dmesg']);(out/'policy-dmesg-before-private.txt').write_bytes(before)
state=dict(state='stop-submitted',old_pid=int(old.name));marker.write_text(json.dumps(state,indent=2)+'\n')
os.kill(int(old.name),signal.SIGTERM)
for _ in range(50):
    if not old.exists():break
    time.sleep(0.1)
assert not old.exists(),'Existing WirePlumber did not terminate; do not duplicate it'
time.sleep(0.5);new=processes('wireplumber');assert len(new)<=1
manually_restarted=not new
if not new:
    user=pwd.getpwuid(10000)
    def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
    state['state']='start-submitted';marker.write_text(json.dumps(state,indent=2)+'\n')
    with (out/'policy-restart-private.log').open('wb') as log:
        child=subprocess.Popen(argv,preexec_fn=demote,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    time.sleep(2);assert child.poll() is None
new=processes('wireplumber');assert len(new)==1;new=new[0]
maps=(new/'maps').read_text();(out/'policy-after-maps-private.txt').write_text(maps)
paths=sorted({line.split()[-1] for line in maps.splitlines() if '/usr/lib/libcamera' in line});assert paths and '(deleted)' not in '\n'.join(line for line in maps.splitlines() if '/usr/lib/libcamera' in line)
manifest=json.loads(Path('/var/lib/samurai/k219-r6-package-candidates/forward-manifest.json').read_text())
expected={name:item['sha256'] for package in manifest['packages'] for name,item in package['files'].items() if item['kind']=='file' and name.startswith('usr/lib/libcamera')}
for name in paths:assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==expected[name.lstrip('/')]
for name,identities in preserved.items():assert {p.name:(p/'stat').read_text().split(') ',1)[1].split()[19] for p in processes(name)}==identities
after=subprocess.check_output(['dmesg']);(out/'policy-dmesg-after-private.txt').write_bytes(after)
faults={k:after.count(v)-before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()};assert not any(faults.values())
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
state.update(state='verified',new_pid=int(new.name));marker.write_text(json.dumps(state,indent=2)+'\n')
report=dict(stage=219,idle_wireplumber_reloaded=True,existing_process_terminated_gracefully=True,manual_restart_required=manually_restarted,new_r6_camera_libraries_loaded=True,no_old_deleted_camera_library_mappings=True,no_candidate_path_environment_overrides=True,pipewire_and_all_desktop_process_identities_unchanged=True,audio_pcm_was_closed=True,taint=0,fault_delta=faults,reboot_not_used=True)
(out/'policy-reload-summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=40);(host.PRIVATE/'policy-reload-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(here/'wireplumber-reload-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
