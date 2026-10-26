"""Verify production stayed untouched after all isolated common-backend experiments."""
from pathlib import Path
import json
import host
R=Path(__file__).parent
inputs=json.loads((R/'common-package-inputs-validation.json').read_text());baseline=json.loads((R/'baseline-validation.json').read_text());launch=json.loads((R.parent/'kernel262/launcher-install-validation.json').read_text())
code=r'''
from pathlib import Path
import hashlib,json,os,pwd,stat,subprocess,sys
inputs,baseline,launch=json.loads(sys.stdin.buffer.readline());root=Path('/var/lib/samurai');out=root/'k263-final-health';assert not out.exists();out.mkdir(mode=0o700)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k260-work/boot-id-private.txt').read_bytes()
assert all(sha(Path(i['path']))==i['sha256'] for i in inputs)
assert sha(Path('/usr/lib/gstreamer-1.0/libgstpipewire.so'))==baseline['plugin_sha256']
for name in ['pipewire-libs','pipewire-spa-libcamera']:subprocess.run(['apk','info','--exists',name+'=1.6.9-r0'],check=True,capture_output=True)
manifest=json.loads((root/'k239-r15-package-candidates/forward-manifest.json').read_text());count=0
for package in manifest['packages']:
 for relative,item in package['files'].items():
  p=Path('/')/relative
  if item['kind']=='symlink':assert p.is_symlink() and os.readlink(p)==item['target']
  else:assert sha(p)==item['sha256'] and stat.S_IMODE(p.stat().st_mode)==item['mode']
  count+=1
assert count==49
user=pwd.getpwuid(10000);expected={x['file']:x['after_sha256'] for x in launch['launcher_files']}
for relative in ['.local/share/applications/org.gnome.Snapshot.desktop','.local/share/dbus-1/services/org.gnome.Snapshot.service']:
 p=Path(user.pw_dir)/relative;assert sha(p)==expected[p.name]
processes=[]
for p in Path('/proc').glob('[0-9]*'):
 try:
  name=(p/'comm').read_text().strip();assert name not in ['snapshot','megapixels']
  if name in ['phosh','pipewire','wireplumber']:processes.append(dict(name=name,pid=int(p.name),start_ticks=(p/'stat').read_text().rsplit(')',1)[1].split()[19]))
 except FileNotFoundError:pass
assert sorted(processes,key=lambda x:x['name'])==sorted(baseline['processes'],key=lambda x:x['name'])
assert all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in baseline['runtime'])
assert not [p for p in Path('/sys/kernel/tracing/instances').iterdir() if p.name.startswith('k263')]
contexts=list(root.glob('k263-pipewire-*-r2'));assert contexts
assert all(json.loads((p/'state-private.json').read_text())['state']=='terminal' for p in contexts)
dmesg=subprocess.check_output(['dmesg']);(out/'dmesg-private.txt').write_bytes(dmesg)
assert dmesg.count(b'gpu fault:')==baseline['gpu_fault_count'] and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
clocks=Path('/sys/kernel/debug/clk/clk_summary').read_text()
assert all(any(line.split()[0]==name and line.split()[1]=='0' for line in clocks.splitlines() if line.split()) for name in ['cam_cc_mclk1_clk','cam_cc_mclk2_clk'])
packages=sum(l.startswith('P:') for l in Path('/lib/apk/db/installed').read_text().splitlines());assert packages==961
report=dict(stage=263,current260_boot_verified=True,production_common_libraries_unchanged=True,production_common_packages='1.6.9-r0',gstreamer_plugin_and_launchers_unchanged=True,camera_framework_payloads_verified=count,package_count=packages,phosh_pipewire_wireplumber_identities_unchanged=True,camera_devices_suspended=True,mclk1_mclk2_disabled=True,trace_instances_removed=True,test_contexts_terminal=len(contexts),gpu_fault_delta=0,taint=0,common_fix_not_deployed=True,temporary_copy_workaround_retained=True,complete_camera_adaptation=False)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
payload=json.dumps([inputs,baseline,launch]).encode()+b'\n'
# Keep the source and manifest in one stdin stream without shell argument limits.
wrapper='import sys;source='+repr(code)+';exec(compile(source,"k263-final-health","exec"))'
import shlex
r=host.ssh('python3 -c '+shlex.quote(wrapper),input=payload,timeout=30)
(host.PRIVATE/'final-health-private.json').write_bytes(r.stdout)
d=json.loads(r.stdout);(R/'final-health-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
