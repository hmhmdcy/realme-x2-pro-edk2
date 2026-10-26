"""Read final idle state only; do not open V4L2 devices or start a camera."""
from pathlib import Path
import importlib.util,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel269')
spec=importlib.util.spec_from_file_location('h',R/'host.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
code=r'''
from pathlib import Path
import hashlib,json,os,stat,struct,subprocess
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def note(p):
 data=p.read_bytes();offset=struct.unpack_from('<Q',data,40)[0];size,count,index=struct.unpack_from('<HHH',data,58)
 sec=[struct.unpack_from('<IIQQQQIIQQ',data,offset+i*size) for i in range(count)]
 strings=data[sec[index][4]:sec[index][4]+sec[index][5]]
 return next(data[s[4]:s[4]+s[5]] for s in sec if strings[s[0]:].split(b'\0',1)[0]==b'.note.gnu.build-id')
mods={}
for name in ['qcom_pm8008','qcom_pm8008_regulator','imx319','imx471','qcom_camss']:
 p=Path('/sys/module',name);file=Path(subprocess.check_output(['modinfo','-n',name],text=True).strip())
 mods[name]=dict(loaded=p.exists(),sha256=sha(file),loaded_note_matches_disk=note(file)==(p/'notes/.note.gnu.build-id').read_bytes())
rails={}
for p in Path('/sys/class/regulator').glob('regulator.*'):
 name=(p/'name').read_text().strip()
 if name.startswith(('cam-front-','cam-rear-')):rails[name]={n:(p/n).read_text().strip() for n in ['state','num_users']}
runtime={n:Path('/sys/bus',bus,'devices',n,'power/runtime_status').read_text().strip() for bus,n in [('i2c','7-0010'),('i2c','9-0010'),('platform','ac4a000.cci'),('platform','ac4b000.cci'),('platform','acb3000.camss')]}
clocks=Path('/sys/kernel/debug/clk/clk_summary').read_text()
mclk={n:next(l.split()[1] for l in clocks.splitlines() if l.split() and l.split()[0]==n) for n in ['cam_cc_mclk1_clk','cam_cc_mclk2_clk']}
services=json.loads(Path('/var/lib/samurai/k269-services-current-private.json').read_text());assert services['boot_id']==Path('/proc/sys/kernel/random/boot_id').read_text().strip()
for row in services['processes']:
 p=Path('/proc',str(row['pid']));assert (p/'comm').read_text().strip()==row['comm'] and (p/'stat').read_text().rsplit(')',1)[1].split()[19]==row['start_ticks']
for p in Path('/proc').glob('[0-9]*'):
 try:assert (p/'comm').read_text().strip() not in ['snapshot','megapixels']
 except OSError:pass
manifest=json.loads(Path('/var/lib/samurai/k268-r19-package-candidates/forward-manifest.json').read_text());count=0
installed=Path('/lib/apk/db/installed').read_text();versions={next(l[2:] for l in b.splitlines() if l.startswith('P:')):next(l[2:] for l in b.splitlines() if l.startswith('V:')) for b in installed.split('\n\n') if any(l.startswith('P:') for l in b.splitlines())}
for package in manifest['packages']:
 assert versions[package['name']]==package['version']
 for relative,item in package['files'].items():
  p=Path('/')/relative
  if item['kind']=='symlink':assert p.is_symlink() and os.readlink(p)==item['target']
  else:assert p.is_file() and not p.is_symlink() and sha(p)==item['sha256'] and stat.S_IMODE(p.stat().st_mode)==item['mode']
  count+=1
dmesg=subprocess.check_output(['dmesg']);faults={k:dmesg.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',modem=b'crash detected in modem',fatal=b'fatal error received',gpu=b'gpu fault:').items()}
rules=Path('/etc/udev/rules.d/99-realme-rmx1931-sensors.rules')
trace={p.name:(p/'tracing_on').read_text().strip() for p in Path('/sys/kernel/tracing/instances').glob('k269*')}
report=dict(stage=269,release=os.uname().release,current_guard='/var/lib/samurai/k269-work/boot-id-private.txt',
 modules=mods,rails=rails,runtime=runtime,mclk_enable_counts=mclk,taint=int(Path('/proc/sys/kernel/tainted').read_text()),
 current_boot_fault_counts=faults,no_live_camera_application=True,stage269_tracing_disabled=all(v=='0' for v in trace.values()),
 services={k:v for k,v in services.items() if k!='boot_id'},camera_package_payload_records_verified=count,
 installed_package_count=len(versions),module_count=len(list(Path('/lib/modules',os.uname().release).rglob('*.ko'))),
 sensor_rule_sha256=sha(rules),greetd_confd_sha256=sha(Path('/etc/conf.d/greetd')),
 lab_modules_absent=not any(Path('/sys/module',n).exists() for n in ['qcom_pm8008_imx319_lab','reset_realme_rmx1931_pm8008']),
 old_lab_config_absent=not Path('/etc/modprobe.d/samurai-pmic-bringup.conf').exists(),no_camera_stream_requested=True)
assert report['taint']==0 and not any(faults.values()) and all(v=='suspended' for v in runtime.values())
assert len(rails)==4 and all(v==dict(state='disabled',num_users='0') for v in rails.values()) and all(v=='0' for v in mclk.values())
assert all(v['loaded'] and v['loaded_note_matches_disk'] for v in mods.values()) and report['stage269_tracing_disabled']
assert report['lab_modules_absent'] and report['old_lab_config_absent']
print(json.dumps(report))
'''
q=h.ssh('python3 -',input=code.encode(),timeout=35);(P/'final-health-private.json').write_bytes(q.stdout);d=json.loads(q.stdout)
old=json.loads((R.parent/'kernel267/postboot-hardware-validation.json').read_text())['modules']
assert all(v['sha256']==old[n]['sha256'] for n,v in d['modules'].items())
(R/'final-health-validation.json').write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps({k:v for k,v in d.items() if k not in ['modules','services']},indent=2))
