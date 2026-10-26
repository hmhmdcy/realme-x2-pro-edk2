"""Read current selected modem configuration only; do not activate anything."""
from pathlib import Path
import json,subprocess
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k244-runtime/boot-id-private.txt').read_bytes()
help=subprocess.run(['qmicli','--help-pdc'],capture_output=True,timeout=10);assert help.returncode==0;lines=help.stdout.decode().splitlines();queries=[line.strip() for line in lines if 'get-selected' in line or 'list-configs' in line]
out={};report={}
for label,option in [('software','--pdc-get-selected-config=software'),('platform','--pdc-get-selected-config=platform')]:
 x=subprocess.run(['qmicli','-p','-d','qrtr://0',option],capture_output=True,timeout=18);out[label]=(x.stdout+x.stderr).decode();report[label]=dict(exit_code=x.returncode,reply_received=bool(x.stdout),not_found='not found' in out[label].lower(),unsupported='not supported' in out[label].lower())
print(json.dumps({'report':dict(stage=245,read_only_pdc_queries=True,queries=queries,status=report),'private':dict(output=out)}))
