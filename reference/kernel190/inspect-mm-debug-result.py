from pathlib import Path
import json
import host

code='''from pathlib import Path
import re,json
log=Path('/var/lib/samurai/k190-mm-reinit-r2/daemon-debug-private.log').read_text()
rows=[]
for line in log.splitlines():
 lower=line.lower()
 if ('assistance' in lower or 'predicted orbit' in lower or
     ('client' in lower and ('pds' in lower or "'loc'" in lower))) and 'http' not in lower:
  # Selected engineering messages do not include position/NMEA/identity payloads.
  rows.append(line)
Path('/var/lib/samurai/k190-mm-reinit-r2/selected-debug-private.txt').write_text('\\n'.join(rows)+'\\n')
print(json.dumps(dict(selected_lines=rows)))
'''
p=host.ssh('python3 -',input=code.encode());(host.PRIVATE/'mm-selected-debug-private.json').write_bytes(p.stdout);print(p.stdout.decode())
