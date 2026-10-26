from pathlib import Path
import json,subprocess
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k244-runtime/boot-id-private.txt').read_bytes();results={};private={}
for name in ['dms-get-operating-mode','loc-get-engine-lock','loc-get-operation-mode','loc-get-nmea-types']:
 x=subprocess.run(['qmicli','-p','-d','qrtr://0','--'+name],capture_output=True,timeout=10);text=(x.stdout+x.stderr).decode();private[name]=text
 results[name]=dict(rc=x.returncode,lines=[line.strip() for line in text.splitlines() if any(k in line.lower() for k in ['mode:','lock:','mask:','nmea types:'])])
print(json.dumps({'report':dict(stage=244,queries=results),'private':private}))
