"""Verify the changed plugin/launchers and the retained camera framework."""
from pathlib import Path
import json,shlex
import host
R=Path(__file__).parent
proof=json.loads((R/'package-install-validation.json').read_text());launch=json.loads((R/'launcher-install-validation.json').read_text());baseline=json.loads((R/'baseline-validation.json').read_text())
code=r'''
from pathlib import Path
import hashlib,json,os,pwd,stat,subprocess,sys
proof,launch,baseline=json.loads(sys.argv[1]);root=Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k260-work/boot-id-private.txt').read_bytes()
out=root/'k262-final-health';assert not out.exists();out.mkdir(mode=0o700)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(Path('/usr/lib/gstreamer-1.0/libgstpipewire.so'))==proof['plugin_sha256']
manifest=json.loads((root/'k239-r15-package-candidates/forward-manifest.json').read_text());count=0
for package in manifest['packages']:
 for relative,item in package['files'].items():
  p=Path('/')/relative
  if item['kind']=='symlink':assert p.is_symlink() and os.readlink(p)==item['target']
  else:assert sha(p)==item['sha256'] and stat.S_IMODE(p.stat().st_mode)==item['mode']
  count+=1
assert count==49
user=pwd.getpwuid(10000)
launch_paths=[Path(user.pw_dir)/'.local/share/applications/org.gnome.Snapshot.desktop',Path(user.pw_dir)/'.local/share/dbus-1/services/org.gnome.Snapshot.service']
expected={x['file']:x['after_sha256'] for x in launch['launcher_files']}
assert all(sha(p)==expected[p.name] for p in launch_paths)
devices=['/sys/bus/i2c/devices/7-0010','/sys/bus/i2c/devices/9-0010','/sys/bus/platform/devices/ac4a000.cci','/sys/bus/platform/devices/ac4b000.cci','/sys/bus/platform/devices/acb3000.camss']
assert all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in devices)
processes=[]
for p in Path('/proc').glob('[0-9]*'):
 try:
  name=(p/'comm').read_text().strip()
  assert name not in ['snapshot','megapixels'],'Camera app still active'
  if name in ['phosh','pipewire','wireplumber']:processes.append(dict(name=name,pid=int(p.name),start_ticks=(p/'stat').read_text().rsplit(')',1)[1].split()[19]))
 except FileNotFoundError:pass
assert sorted(processes,key=lambda x:x['name'])==sorted(baseline['processes'],key=lambda x:x['name'])
assert not [p.name for p in Path('/sys/kernel/tracing/instances').iterdir() if p.name.startswith('k262')]
assert all(json.loads((p/'state-private.json').read_text())['state']=='terminal' for p in root.glob('k262-pipewire-*'))
dmesg=subprocess.check_output(['dmesg']);(out/'dmesg-private.txt').write_bytes(dmesg)
assert dmesg.count(b'gpu fault:')==baseline['gpu_fault_count']
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
report=dict(stage=262,current260_boot_verified=True,plugin_sha256=proof['plugin_sha256'],camera_framework_payloads_verified=count,package_count=sum(l.startswith('P:') for l in Path('/lib/apk/db/installed').read_text().splitlines()),launcher_hashes_verified=True,camera_devices_suspended=True,all_test_workers_terminal=True,trace_instances_removed=True,phosh_pipewire_wireplumber_identities_unchanged=True,gpu_fault_delta=0,taint=0,gui_acceptance_pending=True,complete_camera_adaptation=False)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
r=host.ssh('python3 - '+shlex.quote(json.dumps([proof,launch,baseline])),input=code.encode(),timeout=30)
(host.PRIVATE/'final-health-private.json').write_bytes(r.stdout)
d=json.loads(r.stdout);(R/'final-health-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d))
