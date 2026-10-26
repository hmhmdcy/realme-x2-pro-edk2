"""Check current resource restoration and critical payloads after telephoto experiments."""
from pathlib import Path
import ast,hashlib,json,subprocess
import host
HERE=Path(__file__).resolve().parent
for path in ['delay-capture-r1-validation.json','joint-r1-capture-validation.json','ae-r1-capture-validation.json']:
 assert json.loads((HERE/path).read_text())['passed']
assert json.loads((HERE/'joint-physical-validation.json').read_text())['passed']
assert json.loads((HERE/'ae-r1-association-validation.json').read_text())['passed']
source=(HERE/'native-capture.py').read_text();tree=ast.parse(source)
health=ast.get_source_segment(source,next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='health'))
prior=json.loads((HERE.parent/'kernel305/final-health-validation.json').read_text())
code=r'''
from pathlib import Path
import hashlib,json,os,re,struct,subprocess
HEALTH
state=health();assert not state['taint']
assert len(state['sensors'])==5 and all(v=='suspended' for v in state['sensors'].values())
assert all(v=='suspended' for v in state['platforms'].values())
assert len(state['rails'])==9 and all(v['state']=='disabled' and v['num_users']=='0' for v in state['rails'].values())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def note(path):
 raw=Path(path).read_bytes();off=struct.unpack_from('<Q',raw,40)[0];size,count,index=struct.unpack_from('<HHH',raw,58)
 sections=[struct.unpack_from('<IIQQQQIIQQ',raw,off+i*size) for i in range(count)]
 names=raw[sections[index][4]:sections[index][4]+sections[index][5]]
 return next(raw[s[4]:s[4]+s[5]] for s in sections if names[s[0]:].split(b'\0',1)[0]==b'.note.gnu.build-id')
expected=EXPECTED;modules={}
for name,previous in expected.items():
 p=Path(subprocess.check_output(['modinfo','-n',name],text=True).strip())
 assert sha(p)==previous['sha256'] and Path('/sys/module',name,'notes/.note.gnu.build-id').read_bytes()==note(p)
 modules[name]=dict(sha256=sha(p),loaded_note_matches_disk=True,unchanged_since305=True)
lines=Path('/sys/kernel/debug/clk/clk_summary').read_text().splitlines()
clocks={n:int(next(l.split()[1] for l in lines if l.split() and l.split()[0]==n)) for n in ['cam_cc_mclk0_clk','cam_cc_mclk1_clk','cam_cc_mclk2_clk','cam_cc_mclk3_clk','cam_cc_cci_0_clk','cam_cc_cci_1_clk']}
assert not any(clocks.values())
original=Path('/var/lib/samurai/k305-geometry-r3')
pre=json.loads((original/'preflight-private.json').read_text());summary=json.loads((original/'summary-private.json').read_text())
services=[pre['services'][n] for n in ['phoc','phosh']]+summary['new_services']
for item in services:
 fields=Path('/proc',str(item['pid']),'stat').read_text().rsplit(')',1)[1].split()
 assert fields[0]!='Z' and fields[19]==item['start_ticks']
for n in ['lib/apk/db/installed','etc/apk/world']:assert Path('/'+n).read_bytes()==(original/'backup'/n).read_bytes()
workers=[]
for p in Path('/proc').glob('[0-9]*'):
 try:
  fields=(p/'stat').read_text().rsplit(')',1)[1].split()
  if fields[0]!='Z' and b'/var/lib/samurai/k306-' in (p/'cmdline').read_bytes():workers.append(int(p.name))
 except (FileNotFoundError,ProcessLookupError):pass
assert not workers
data=subprocess.check_output(['dmesg'])
faults={k:data.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu_fault=b'gpu fault:',fatal=b'fatal error received',modem=b'crash detected in modem').items()}
assert not any(faults.values()) and not list(Path('/sys/fs/pstore').glob('*'))
cci_errors=[l for l in data.decode(errors='replace').splitlines() if 'i2c-qcom-cci' in l and any(s in l.lower() for s in ['timeout','failed','nack'])]
assert not cci_errors
assert not any('k306-oem-tele-tuning-ro' in l for l in Path('/proc/mounts').read_text().splitlines())
print(json.dumps(dict(stage=306,kernel_build=298,same305_boot_guard=True,health=state,clocks=clocks,
 critical_modules=modules,critical_module_count=len(modules),full778_module_inventory_not_repeated=True,
 package_database_world_unchanged=True,desktop_pw_wp_identities_unchanged=True,
 matching_camera_workers_live=workers,faults=faults,cci_errors=0,pstore_files=0,
 factory_vendor_mount_released=True,no_system_library_replacement=True,no_phone_reboot_or_flash=True,
 product_camera_path='RAW plus CPU ISP',whole_system_healthy=False,checked_camera_runtime_healthy=True)))
'''.replace('HEALTH',health).replace('EXPECTED',repr(prior['modules']))
q=host.ssh('python3 -',input=code.encode(),timeout=30)
(host.PRIVATE/'final-health-private.json').write_bytes(q.stdout)
d=json.loads(q.stdout)
(HERE/'final-health-validation.json').write_text(json.dumps(d,indent=2)+'\n')
kernel=Path('/home/cy122/x2pro-linux/camera305-sensor-kernel')
assert subprocess.check_output(['git','-C',str(kernel),'rev-parse','HEAD'],text=True).strip()=='18b0a5a753e9363594f682049bf131169488c644'
assert not subprocess.check_output(['git','-C',str(kernel),'status','--porcelain'])
sdk=Path('/home/cy122/x2pro-linux/libcamera214-root/work/libcamera299-inline')
baseline=json.loads((HERE.parent/'kernel303/build-validation.json').read_text())
assert all(hashlib.sha256((sdk/n).read_bytes()).hexdigest()==digest for n,digest in baseline['source_sha256'].items())
d.update(kernel_source_unchanged=True,candidate303_source_unchanged=True)
(HERE/'final-health-validation.json').write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps({k:v for k,v in d.items() if k not in ['health','critical_modules']},indent=2))
