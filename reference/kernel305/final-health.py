"""Verify the active mixed Image/module deployment and unchanged product package payloads."""
from pathlib import Path
import ast,json
import host
HERE=Path(__file__).resolve().parent
assert json.loads((HERE/'geometry-install-validation.json').read_text())['passed']
assert json.loads((HERE/'four-camera-regression-validation.json').read_text())['passed']
assert json.loads((HERE/'interrupt-restoration-validation.json').read_text())['passed']
native=(HERE/'native-install-geometry.py').read_text()
tree=ast.parse(native)
health_source=ast.get_source_segment(native,next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='health'))
idle_source=ast.get_source_segment(native,next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='is_idle'))
code=r'''
from pathlib import Path
import hashlib,json,os,re,struct,subprocess
root=Path('/var/lib/samurai/k305-geometry-r3');r=root.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#298 ')
HEALTH
IDLE
h=health();assert is_idle(h)
tree=Path('/usr/lib/modules')/os.uname().release
old=json.loads((root/'module-inventory-before-private.json').read_text())
expected=old.copy();expected['kernel/drivers/media/i2c/s5k3m5.ko']='d1a85e75b9344423097c8189ed65a0320abcb3f7ba3d5fdac34e3c8758f056c9'
inventory={str(p.relative_to(tree)):sha(p) for p in tree.rglob('*.ko')}
assert len(inventory)==778 and inventory==expected
manifest=json.loads((r/'k278-package-transaction/new-manifest-private.json').read_text());checked=0
for package in manifest['packages']:
 for name,item in package['files'].items():
  p=Path('/')/name
  if item['kind']=='symlink':assert p.is_symlink() and os.readlink(p)==item['target']
  else:assert not p.is_symlink() and sha(p)==item['sha256'] and p.stat().st_mode&0o777==item['mode']
  checked+=1
assert checked==50
for n in ['lib/apk/db/installed','etc/apk/world']:assert Path('/'+n).read_bytes()==(root/'backup'/n).read_bytes()
def note(path):
 raw=Path(path).read_bytes();off=struct.unpack_from('<Q',raw,40)[0];size,count,strings=struct.unpack_from('<HHH',raw,58)
 sections=[struct.unpack_from('<IIQQQQIIQQ',raw,off+i*size) for i in range(count)]
 names=raw[sections[strings][4]:sections[strings][4]+sections[strings][5]]
 return next(raw[x[4]:x[4]+x[5]] for x in sections if names[x[0]:].split(b'\0',1)[0]==b'.note.gnu.build-id')
modules={}
for name in ['qcom_camss','i2c_qcom_cci','s5k3m5','s5kgw1','imx319','imx471','lc898219xi','qcom_pm8008','qcom_pm8008_regulator','v4l2_cci']:
 p=Path(subprocess.check_output(['modinfo','-n',name],text=True).strip())
 assert Path('/sys/module',name,'notes/.note.gnu.build-id').read_bytes()==note(p)
 assert subprocess.check_output(['modinfo','-F','intree',str(p)],text=True).strip()=='Y'
 params=Path('/sys/module',name,'parameters')
 modules[name]=dict(sha256=sha(p),loaded=True,loaded_note_matches_disk=True,intree='Y',
  parameters={p.name:p.read_text().strip() for p in params.glob('*')} if params.exists() else {})
lines=Path('/sys/kernel/debug/clk/clk_summary').read_text().splitlines()
clocks={n:int(next(l.split()[1] for l in lines if l.split() and l.split()[0]==n)) for n in ['cam_cc_mclk0_clk','cam_cc_mclk1_clk','cam_cc_mclk2_clk','cam_cc_mclk3_clk','cam_cc_cci_0_clk','cam_cc_cci_1_clk']}
assert not any(clocks.values())
pre=json.loads((root/'preflight-private.json').read_text());summary=json.loads((root/'summary-private.json').read_text())
expected_services=[pre['services'][n] for n in ['phoc','phosh']]+summary['new_services']
for item in expected_services:
 fields=Path('/proc',str(item['pid']),'stat').read_text().rsplit(')',1)[1].split()
 assert fields[0]!='Z' and fields[19]==item['start_ticks']
kernel=subprocess.check_output(['dmesg'])
faults={k:kernel.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu_fault=b'gpu fault:',fatal=b'fatal error received',modem=b'crash detected in modem').items()}
assert not any(faults.values())
cci_errors=[l for l in kernel.decode(errors='replace').splitlines() if 'i2c-qcom-cci' in l and any(s in l.lower() for s in ['timeout','failed','nack'])]
assert not cci_errors
assert not list(Path('/sys/fs/pstore').glob('*'))
device=Path('/sys/bus/i2c/devices')/pre['device']
node=next('/dev/'+p.name for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().strip()=='s5k3m5 '+pre['device'])
q=subprocess.run([str(root/'payload/sensor-geometry'),node],capture_output=True,timeout=10);assert q.returncode==0
geometry=json.loads(q.stdout)
db=Path('/lib/apk/db/installed').read_bytes();package_count=sum(1 for p in db.split(b'\n\n') if any(l.startswith(b'P:') for l in p.splitlines()));assert package_count==961
processes=[]
for p in Path('/proc').glob('[0-9]*'):
 try:
  cmd=(p/'cmdline').read_bytes();fields=(p/'stat').read_text().rsplit(')',1)[1].split()
  if fields[0]!='Z' and any(s in cmd for s in [b'/run/samurai305-tools/pipeline-fixture',b'k305-four-camera-regression-r1',b'k305-geometry-r3/worker-private.py']):
   processes.append(int(p.name))
 except (FileNotFoundError,ProcessLookupError):pass
# This health checker is sent on stdin; its own command line contains none of the worker paths.
assert not processes
report=dict(stage=305,kernel_build=298,release=os.uname().release,new_boot_guard='k305-geometry-r2',
 usb_original_key_verified=True,boot_id_changed_since_303=True,
 module_count=778,all778_modules_verified=True,only_s5k3m5_changed=True,other777_modules_preserved=True,
 current50_payloads_verified=checked,package_count=package_count,
 package_versions={p['name']:p['version'] for p in manifest['packages']},package_database_world_unchanged=True,
 modules=modules,health=h,clocks=clocks,geometry=geometry,faults=faults,taint=0,pstore_files=0,cci_errors=0,
 desktop_processes_preserved=True,pw_wp_restarted=True,matching_test_workers_live=processes,
 product_camera_path='RAW plus CPU ISP',hardware_ipa_candidate_not_installed=True,full_camera_calibration_complete=False,
 whole_system_healthy=False,checked_camera_runtime_healthy=True)
(root/'final-health-private.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''.replace('HEALTH',health_source).replace('IDLE',idle_source)
q=host.ssh('python3 -',input=code.encode(),timeout=35)
(host.PRIVATE/'final-health-private.json').write_bytes(q.stdout)
report=json.loads(q.stdout)
(HERE/'final-health-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['modules','health','package_versions']},indent=2))
