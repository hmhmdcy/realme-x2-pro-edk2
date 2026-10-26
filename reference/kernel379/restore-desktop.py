"""Restore the normal desktop without retrying the failed SLPI attach this boot."""
from pathlib import Path
import json
import host
R=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import hashlib,json,os,re,subprocess,time
r=Path('/var/lib/samurai');out=r/'k379-desktop-restore-r1';out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k378-recovered/boot-id-private.txt').read_bytes()
for name in ['s5kgw1','imx471','imx319','s5k3m5']:
 devices=[p for p in Path('/sys/bus/i2c/drivers',name).glob('*') if p.is_symlink() and re.fullmatch(r'\d+-[0-9a-f]{4}',p.name)]
 assert len(devices)==1 and (devices[0]/'power/runtime_status').read_text().strip()=='suspended'
record=json.loads(Path('/run/samurai-ssc/state.json').read_text());assert record['attempted'] and not record['started'] and record['stopped']
assert next((p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('*') if (p/'name').read_text().strip()=='slpi')=='offline'
config=Path('/etc/conf.d/greetd').read_bytes();assert subprocess.run(['rc-service','greetd','status'],capture_output=True).returncode!=0
q=subprocess.run(['rc-service','--nodeps','greetd','start'],capture_output=True,timeout=35);(out/'start-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0
deadline=time.monotonic()+20
while time.monotonic()<deadline:
 processes=[]
 for p in Path('/proc').glob('[0-9]*'):
  try:
   name=(p/'comm').read_text().strip()
   if name in ['phoc','phosh','pipewire','wireplumber'] and (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z':processes.append(dict(comm=name,pid=int(p.name),start_ticks=(p/'stat').read_text().rsplit(')',1)[1].split()[19]))
  except OSError:pass
 if {p['comm'] for p in processes}=={'phoc','phosh','pipewire','wireplumber'}:break
 time.sleep(.5)
assert {p['comm'] for p in processes}=={'phoc','phosh','pipewire','wireplumber'} and len(processes)==4
assert Path('/etc/conf.d/greetd').read_bytes()==config
report=dict(stage=379,desktop_started=True,processes=processes,temporary_nodeps_start=True,dependency_config_unchanged=True,
 failed_slpi_start_not_retried=True,sensor_rotation_unavailable_pending_ssc_fix=True)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');(r/'k379-services-current-private.json').write_text(json.dumps(dict(boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),processes=processes)))
print(json.dumps(report))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=65,check=False);(host.PRIVATE/'desktop-restore-response-private.log').write_bytes(q.stdout+q.stderr)
assert q.returncode==0 and q.stdout,'Inspect the same desktop start before retrying'
d=json.loads(q.stdout);(R/'desktop-restore-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
