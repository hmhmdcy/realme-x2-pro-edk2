from pathlib import Path
import json,shlex
import host
code=r'''from pathlib import Path
import json
r=Path('/var/lib/samurai/k441-variable-pd10-r3');s=(r/'kernel-log-private.txt').read_text().splitlines();contexts=[]
for i,l in enumerate(s):
 if 'Missing SOF' in l:contexts.append(s[max(0,i-8):i+8])
captures={}
for p in r.glob('*/client.log'):
 t=p.read_text().splitlines();captures[p.parent.name]=[l for l in t if any(k in l for k in ['START_STATUS','FIXTURE_CHILD','IPE_TONE_STOP','IPE_HISTORY_STOP','Resynced','Camera sensor','stream','Stream','ADAPT_PID'])][:22]
print(json.dumps(dict(contexts=contexts,captures=captures)))
'''
q=host.ssh('python3 -c '+shlex.quote(code),timeout=20);q.check_returncode();(host.PRIVATE/'sof-diagnostics-private.json').write_bytes(q.stdout);print(q.stdout.decode())
