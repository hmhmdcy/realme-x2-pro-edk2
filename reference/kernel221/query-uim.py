from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,os,re,subprocess
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k221-baseline/boot-id-private.txt').read_bytes()
out=root/'k221-uim-readonly';assert not out.exists();out.mkdir(mode=0o700)
r=dict(stage=221,read_only=True,queries={})
for option in ['uim-get-card-status','uim-get-slot-status']:
 p=subprocess.run(['qmicli','-d','qrtr://0','--'+option],capture_output=True,text=True,timeout=30)
 text=p.stdout+p.stderr;(out/(option+'-private.txt')).write_text(text)
 safe=[l.strip() for l in text.splitlines() if re.search(r'^\s*(?:Card \[|Physical slot|Logical slot|Card state:|Card error:|Slot state:|Card applications:|Application state:|Application type:|error:)',l)]
 r['queries'][option]=dict(exit=p.returncode,status_lines=safe)
(out/'summary.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=85);(host.PRIVATE/'uim-query-host-private.log').write_bytes(p.stdout+p.stderr)
r=json.loads(p.stdout);(here/'uim-readonly-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
