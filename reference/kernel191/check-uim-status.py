from pathlib import Path
import json
import host
code=b'''from pathlib import Path
import json,re,subprocess
out=Path('/var/lib/samurai/k191-uim-status');out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k189r2-reboot-runtime/boot-id-private.txt').read_bytes()
results=[]
for option in ['uim-get-card-status','uim-get-slot-status']:
 p=subprocess.run(['qmicli','-d','qrtr://0','--'+option],capture_output=True,timeout=25)
 (out/(option+'-private.txt')).write_bytes(p.stdout+p.stderr)
 text=p.stdout.decode();states=[]
 for line in text.splitlines():
  if any(label in line.lower() for label in ['card state','slot state','card status','slot status']):
   values=re.findall(r"'([a-z_-]+)'",line.lower());states.extend(values)
 results.append(dict(option=option,exit=p.returncode,states=states))
record=dict(stage=191,read_only=True,results=results)
(out/'summary.json').write_text(json.dumps(record,indent=2)+'\\n');print(json.dumps(record))
'''
p=host.ssh('python3 -',input=code,timeout=60);report=json.loads(p.stdout)
(Path(__file__).resolve().parent/'uim-status-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
