"""Verify the deployed shared path after native, GStreamer and real GUI clients."""
from pathlib import Path
import json,shlex
import host
R=Path(__file__).parent
proof=json.loads((R/'package-install-validation.json').read_text());base=json.loads((R/'baseline-validation.json').read_text());launch=json.loads((R/'launcher-update-validation.json').read_text())
code=r'''
from pathlib import Path
import hashlib,json,os,pwd,re,stat,subprocess,sys
os.umask(0o077);proof,base,launch=json.loads(sys.stdin.buffer.readline());root=Path('/var/lib/samurai');out=root/'k264-final-health'
if out.exists():assert not list(out.iterdir()),'Inspect partial evidence before resuming'
else:out.mkdir()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k260-work/boot-id-private.txt').read_bytes()
for name,digest in proof['payload_sha256'].items():assert sha(Path('/')/name)==digest
assert sha(Path('/usr/lib/gstreamer-1.0/libgstpipewire.so'))==base['plugin_sha256']
for name in ['pipewire-libs','pipewire-spa-libcamera']:subprocess.run(['apk','info','--exists',name+'=1.6.9-r2'],check=True,capture_output=True)
packages=sum(l.startswith('P:') for l in Path('/lib/apk/db/installed').read_text().splitlines());assert packages==961
world=Path('/etc/apk/world').read_text().splitlines();assert all(x in world for x in proof['world_entries_added'])
manifest=json.loads((root/'k239-r15-package-candidates/forward-manifest.json').read_text());count=0
for package in manifest['packages']:
 for name,item in package['files'].items():
  p=Path('/')/name
  if item['kind']=='symlink':assert p.is_symlink() and os.readlink(p)==item['target']
  else:assert sha(p)==item['sha256'] and stat.S_IMODE(p.stat().st_mode)==item['mode']
  count+=1
assert count==49
user=pwd.getpwuid(10000);expected={x['file']:x['after_sha256'] for x in launch['launcher_files']}
for relative in ['.local/share/applications/org.gnome.Snapshot.desktop','.local/share/dbus-1/services/org.gnome.Snapshot.service']:
 p=Path(user.pw_dir)/relative;assert sha(p)==expected[p.name] and b'SAMURAI_CAMERA_COPY' not in p.read_bytes()
services=json.loads((root/'k264-services-current-private.json').read_text())['new_processes'];phosh=next(i for i in base['processes'] if i['name']=='phosh')
expected_processes=services+[phosh];actual=[]
for p in Path('/proc').glob('[0-9]*'):
 try:
  name=(p/'comm').read_text().strip();assert name not in ['snapshot','megapixels']
  if name in ['phosh','pipewire','wireplumber']:actual.append(dict(name=name,pid=int(p.name),start_ticks=(p/'stat').read_text().rsplit(')',1)[1].split()[19]))
 except FileNotFoundError:pass
assert sorted(actual,key=lambda i:i['name'])==sorted(expected_processes,key=lambda i:i['name'])
for i in services:
 p=Path('/proc',str(i['pid']));maps=(p/'maps').read_text();assert '/usr/lib/libpipewire-0.3.so.0.1609.0' in maps
 assert not any('/var/lib/samurai/k264-' in l and '.so' in l for l in maps.splitlines())
 if i['name']=='wireplumber':assert '/usr/lib/spa-0.2/libcamera/libspa-libcamera.so' in maps
 env={k.decode():v.decode() for x in (p/'environ').read_bytes().split(b'\0') if b'=' in x for k,v in [x.split(b'=',1)]}
 assert not any(k in env for k in ['LD_PRELOAD','LD_LIBRARY_PATH','PIPEWIRE_REMOTE','PIPEWIRE_CONFIG_DIR','PIPEWIRE_CONFIG_NAME','PIPEWIRE_RUNTIME_DIR','SPA_PLUGIN_DIR','SAMURAI_CAMERA_COPY'])
states=list(root.glob('k264-*/state-private.json'));assert len(states)==25
for p in states:
 d=json.loads(p.read_text());assert d.get('state')=='terminal' or d.get('terminal') is True,p.parent.name
 if 'pid' in d:
  proc=Path('/proc',str(d['pid']))
  assert not proc.exists() or (proc/'stat').read_text().rsplit(')',1)[1].split()[19]!=d.get('start_ticks'),p.parent.name
assert all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in base['runtime'])
assert not [p for p in Path('/sys/kernel/tracing/instances').iterdir() if p.name.startswith('k264')]
clocks=Path('/sys/kernel/debug/clk/clk_summary').read_text();(out/'clocks-private.txt').write_text(clocks)
assert all(any(l.split()[0]==name and l.split()[1]=='0' for l in clocks.splitlines() if l.split()) for name in ['cam_cc_mclk1_clk','cam_cc_mclk2_clk'])
controls=[]
for p in Path('/sys/class/video4linux').glob('v4l-subdev*'):
 name=(p/'name').read_text().strip()
 if not name.startswith(('imx319','imx471','msm_csid')):continue
 listing=subprocess.check_output(['v4l2-ctl','-d','/dev/'+p.name,'--list-ctrls']).decode()
 wanted=[x for x in ['test_pattern','horizontal_flip','vertical_flip'] if re.search(r'\b'+x+r'\s+0x',listing)]
 if wanted:
  values=subprocess.check_output(['v4l2-ctl','-d','/dev/'+p.name,'--get-ctrl='+','.join(wanted)]).decode();pairs=re.findall(r'(\w+):\s*(-?\d+)',values)
  assert len(pairs)==len(wanted) and all(int(v)==0 for k,v in pairs);controls.append(name)
before=(root/'k264-pipewire-6000041-r2/dmesg-before-private.txt').read_bytes();after=subprocess.check_output(['dmesg']);(out/'dmesg-private.txt').write_bytes(after)
faults={k:after.count(v)-before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',fatal=b'fatal error received',bt=b'Frame reassembly failed').items()}
assert not any(faults.values()) and after.count(b'gpu fault:')==base['gpu_fault_count'] and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
report=dict(stage=264,current260_boot_verified=True,production_common_packages='1.6.9-r2',production_system_library_hashes_verified=True,gstreamer_plugin_unchanged=True,copy_opt_in_absent_from_launchers=True,camera_framework_payloads_verified=count,package_count=packages,world_pins_verified=True,phosh_identity_unchanged=True,production_pipewire_and_wireplumber_identities=services,all_natural_production_tests_and_gui_used_same_daemons=True,system_paths_mapped_no_candidate_overrides=True,camera_devices_suspended=True,mclk1_mclk2_disabled=True,test_patterns_and_flips_zero=True,controls_checked_entities=len(controls),trace_instances_removed=True,test_contexts_terminal=len(states),fault_delta=faults,taint=0,common_fix_deployed=True,complete_camera_adaptation=False)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
payload=json.dumps([proof,base,launch]).encode()+b'\n';wrapper='import sys;source='+repr(code)+';exec(compile(source,"k264-final-health","exec"))'
q=host.ssh('python3 -c '+shlex.quote(wrapper),input=payload,timeout=30,check=False);(host.PRIVATE/'final-health-private.log').write_bytes(q.stdout+q.stderr)
assert q.returncode==0,'Inspect saved final health; do not replay a partial context'
d=json.loads(q.stdout);(R/'final-health-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
