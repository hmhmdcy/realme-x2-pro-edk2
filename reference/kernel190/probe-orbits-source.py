import json
import host

code='''from pathlib import Path
import subprocess,json,os
os.umask(0o077)
out=Path('/var/lib/samurai/k190-orbits');assert not out.exists();out.mkdir(mode=0o700)
results={}
for option in ['loc-get-predicted-orbits-data-source','loc-get-predicted-orbits-data-validity','loc-get-operation-mode','loc-get-engine-lock']:
 p=subprocess.run(['qmicli','-d','qrtr://0','--'+option],capture_output=True,timeout=25)
 raw=(p.stdout+p.stderr).decode(errors='replace');(out/(option+'-private.txt')).write_bytes(p.stdout+p.stderr)
 results[option]=dict(exit=p.returncode,not_supported='NotSupported' in raw or 'not supported' in raw.lower(),
  operation_standalone='standalone' in raw.lower(),engine_unlocked="'none'" in raw.lower(),
  data_source_reported=('server' in raw.lower() or 'maximum' in raw.lower()) and p.returncode==0)
(out/'summary.json').write_text(json.dumps(results,indent=2)+'\\n');print(json.dumps(results))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=115);(host.PRIVATE/'orbits-probe-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);from pathlib import Path
(Path(__file__).resolve().parent/'orbits-source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
