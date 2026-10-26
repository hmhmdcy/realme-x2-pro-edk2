"""Record the deployed three-sensor state and idle resources after actual captures."""
from pathlib import Path
import hashlib,json
import host
R=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import hashlib,json,os,subprocess
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
runtime={}
for bus,names in [('i2c',['7-0010','8-002d','9-0010']),('platform',['ac4a000.cci','ac4b000.cci','acb3000.camss'])]:
 for name in names:runtime[name]=Path('/sys/bus',bus,'devices',name,'power/runtime_status').read_text().strip()
rails={}
for p in Path('/sys/class/regulator').glob('regulator.*'):
 name=(p/'name').read_text().strip()
 if name.startswith(('cam-front-','cam-rear-','cam-tele-')):rails[name]={n:(p/n).read_text().strip() for n in ['state','num_users','microvolts']}
kernel=subprocess.check_output(['dmesg']);clocks=Path('/sys/kernel/debug/clk/clk_summary').read_text();processes=[];services=[]
for p in Path('/proc').glob('[0-9]*'):
 try:
  name=(p/'comm').read_text().strip()
  if name in ['snapshot','megapixels','cam','gst-launch-1.0']:processes.append(dict(pid=int(p.name),comm=name))
  if name in ['phoc','phosh','pipewire','wireplumber','iio-sensor-prox']:
   services.append(dict(pid=int(p.name),comm=name,start_ticks=(p/'stat').read_text().rsplit(')',1)[1].split()[19]))
 except OSError:pass
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();assert boot==Path('/var/lib/samurai/k270-work/boot-id-private.txt').read_text().strip()
manifest=Path('/var/lib/samurai/k270-services-current-private.json');manifest.write_text(json.dumps(dict(boot_id=boot,processes=services),indent=2)+'\n')
report=dict(stage=270,release=os.uname().release,kernel_build=183,module_count=len(list((Path('/usr/lib/modules')/os.uname().release).rglob('*.ko'))),
 package_count=len(subprocess.check_output(['apk','info']).splitlines()),package_database_sha256=sha('/lib/apk/db/installed'),
 runtime=runtime,rails=rails,mclk_enable_counts={name:int(next(l.split()[1] for l in clocks.splitlines() if l.split() and l.split()[0]==name)) for name in ['cam_cc_mclk1_clk','cam_cc_mclk2_clk','cam_cc_mclk3_clk']},
 camera_clients=processes,services=services,taint=int(Path('/proc/sys/kernel/tainted').read_text()),
 faults={k:kernel.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',fatal=b'fatal error received',modem=b'crash detected in modem').items()},
 pstore={p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in Path('/sys/fs/pstore').glob('*') if p.is_file()},
 dmesg=kernel.decode(errors='replace'))
print(json.dumps(report))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=25)
(host.PRIVATE/'final-health-private.json').write_bytes(q.stdout);d=json.loads(q.stdout);d.pop('dmesg')
baseline=json.loads((host.PRIVATE/'deployment-baseline-private.json').read_text())
assert d['package_database_sha256']==baseline['package_db_sha256'];d.pop('package_database_sha256')
assert d['taint']==0 and not any(d['faults'].values()) and not d['camera_clients']
assert all(v=='suspended' for v in d['runtime'].values()) and len(d['rails'])==6
assert all(v['state']=='disabled' and v['num_users']=='0' for v in d['rails'].values()) and not any(d['mclk_enable_counts'].values())
d['package_database_unchanged']=True
(R/'final-health-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
