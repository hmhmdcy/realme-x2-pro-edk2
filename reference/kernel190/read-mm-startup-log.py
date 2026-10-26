from pathlib import Path
import json
import host

code='''from pathlib import Path
import os,re,json,subprocess
os.umask(0o077)
root=Path('/var/lib/samurai/k190-mm-diagnostics')
p=subprocess.run(['logread'],capture_output=True,timeout=15)
(root/'logread-private.txt').write_bytes(p.stdout+p.stderr)
raw=p.stdout.decode(errors='replace')
patterns=['supported assistance data','predicted orbits','assistance data','operation timed out','injecting gpsOneXTRA']
rows=[]
for line in raw.splitlines():
 if 'ModemManager' not in line:continue
 if any(key.lower() in line.lower() for key in patterns):rows.append(line)
(root/'assistance-log-private.txt').write_text('\\n'.join(rows)+'\\n')
# Only error categories are exported, not raw messages or modem identifiers.
report=dict(logread_exit=p.returncode,logread_bytes=len(p.stdout),assistance_related_lines=len(rows),
 timed_out_lines=sum('timed out' in line.lower() for line in rows),unsupported_lines=sum('not supported' in line.lower() for line in rows))
for line in rows:
 match=re.search(r"[Cc]ouldn.t load supported assistance data[^:]*:\\s*(.*)",line)
 if match:report.setdefault('load_errors',[]).append(match[1])
print(json.dumps(report))
'''
p=host.ssh('python3 -',input=code.encode());(host.PRIVATE/'mm-startup-log-summary-private.json').write_bytes(p.stdout)
report=json.loads(p.stdout);(Path(__file__).resolve().parent/'mm-assistance-log-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
