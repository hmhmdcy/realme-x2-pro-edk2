"""Read final module, package, service and power state without requesting frames."""
from pathlib import Path
import ast,json,host
R=Path(__file__).resolve().parent
tree=ast.parse((R.parent/'kernel267/check-postboot.py').read_text())
node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='code' for t in n.targets))
code=ast.literal_eval(node.value).replace('print(json.dumps(report))','')
code+=r'''
import stat
manifest=json.loads((r/'k268-r19-package-candidates/forward-manifest.json').read_text());count=0
names={p['name'] for p in manifest['packages']}
def records(data):
 return {next(l[2:] for l in block.splitlines() if l.startswith('P:')):block for block in data.decode().split('\n\n') if any(l.startswith('P:') for l in block.splitlines())}
old=records((r/'k268-r19-package-transaction/installed-before-private.txt').read_bytes());new=records(Path('/lib/apk/db/installed').read_bytes())
assert set(old)==set(new) and len(new)==961
assert all(new[n]==v for n,v in old.items() if n not in names)
for package in manifest['packages']:
 assert 'V:'+package['version'] in new[package['name']].splitlines()
 for relative,item in package['files'].items():
  p=Path('/')/relative
  if item['kind']=='symlink':assert p.is_symlink() and os.readlink(p)==item['target']
  else:assert p.is_file() and not p.is_symlink() and sha(p)==item['sha256'] and stat.S_IMODE(p.stat().st_mode)==item['mode']
  count+=1
services=json.loads((r/'k268-services-current-private.json').read_text())
for item in services['new_processes']:
 p=Path('/proc',str(item['pid']));assert (p/'stat').read_text().rsplit(')',1)[1].split()[19]==item['start_ticks']
 assert '/usr/lib/libpipewire-0.3.so.0.1609.0' in (p/'maps').read_text()
 assert not any('/var/lib/samurai/k' in line and '.so' in line for line in (p/'maps').read_text().splitlines())
 if item['name']=='wireplumber':assert '/usr/lib/spa-0.2/libcamera/libspa-libcamera.so' in (p/'maps').read_text()
assert not any((p/'comm').exists() and (p/'comm').read_text().strip()=='snapshot' for p in Path('/proc').glob('[0-9]*'))
clocks=report['clock_summary'];report['mclk1_mclk2_disabled']=all(any(l.split()[0]==n and l.split()[1]=='0' for l in clocks.splitlines() if l.split()) for n in ['cam_cc_mclk1_clk','cam_cc_mclk2_clk'])
report['all_five_camera_devices_suspended']=all(Path('/sys/bus',bus,'devices',n,'power/runtime_status').read_text().strip()=='suspended' for bus,n in [('i2c','7-0010'),('i2c','9-0010'),('platform','ac4a000.cci'),('platform','ac4b000.cci'),('platform','acb3000.camss')])
baseline=(r/'k268-snapshot-gui-r5/dmesg-before-private.txt').read_bytes();after=report['dmesg'].encode()
report['fault_delta_since_gui_r5']={k:after.count(v)-baseline.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',fatal=b'fatal error received',bt=b'Frame reassembly failed').items()}
report.update(stage=268,verified_camera_payload_records=count,installed_package_count=len(new),unrelated_954_package_records_unchanged=True,
 system_services=services,session_cleanup_verified=json.loads((r/'k268-unlocked-session-r2/cleanup-private.json').read_text()),
 no_live_snapshot_process=True,ko_count=len(list(Path('/lib/modules',os.uname().release).rglob('*.ko'))),no_frames_requested=True)
for key in ['taint']:assert report[key]==0
assert not any(report['fault_delta_since_gui_r5'].values())
assert report['mclk1_mclk2_disabled'] and report['all_five_camera_devices_suspended']
assert all(v['state']=='disabled' and v['num_users']=='0' for v in report['rails'].values())
assert report['lab_modules_absent'] and report['old_lab_config_absent'] and report['old_reset_dt_node_absent']
assert all(v['loaded'] and v['loaded_note_matches_disk'] for v in report['modules'].values())
print(json.dumps(report))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=40)
(host.PRIVATE/'final-health-private.json').write_bytes(q.stdout);d=json.loads(q.stdout)
initial=json.loads((R.parent/'kernel267/postboot-hardware-validation.json').read_text())
for n,v in initial['modules'].items():assert d['modules'][n]['sha256']==v['sha256']
public={k:v for k,v in d.items() if k not in ['dmesg','clock_summary','regulator_summary','cam_help']}
(R/'final-health-validation.json').write_text(json.dumps(public,indent=2)+'\n')
print(json.dumps({k:d[k] for k in ['stage','taint','verified_camera_payload_records','installed_package_count','ko_count','all_five_camera_devices_suspended','mclk1_mclk2_disabled','fault_delta_since_gui_r5','no_live_snapshot_process']}))
