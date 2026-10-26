from pathlib import Path
import json
import host
code=r'''
from pathlib import Path
import json
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
count=0
for p in Path('/proc').glob('[0-9]*'):
 try:c=p.joinpath('cmdline').read_bytes()
 except OSError:continue
 if b'/var/lib/samurai/k237-tools/native-capture-r2.py\0' in c:count+=1
print(json.dumps(dict(stage=237,r2_context_exists=(r/'k237-capture-rear-raw-r2').exists(),r2_live_worker_count=count,r1_launcher_receipt_exists=(r/'k237-tools/capture-rear-raw-launch-private.log').exists(),actual_fullres_default=Path('/sys/module/imx471/parameters/unprocessed_fullres').read_text().strip())))
'''
r=host.ssh('python3 -',input=code.encode(),timeout=12);(host.PRIVATE/'r2-launch-inspection-private.log').write_bytes(r.stdout+r.stderr);data=json.loads(r.stdout)
assert not data['r2_context_exists'] and data['r2_live_worker_count']==0
receipt=(host.PRIVATE/'transport-last-failure-private.log').read_text()
assert "FileExistsError:" in receipt and 'capture-rear-raw-launch-private.log' in receipt
(Path(__file__).resolve().parent/'r2-launch-validation.json').write_text(json.dumps(data,indent=2)+'\n');print(json.dumps(dict(**data,launcher_stopped_before_popen=True)))
