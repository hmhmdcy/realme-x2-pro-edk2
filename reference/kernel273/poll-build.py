from pathlib import Path
import json
import host
p=host.PRIVATE/'r21-build-state-private.json'
if not p.exists():
 print(json.dumps(dict(state_file_present=False)));raise SystemExit(0)
d=json.loads(p.read_text());pid=d.get('pid');process=Path('/proc',str(pid)) if pid else None
live=False
if process and process.exists():
 try:
  fields=(process/'stat').read_text().rsplit(')',1)[1].split()
  live=fields[0]!='Z' and fields[19]==d.get('start_ticks')
 except OSError:pass
print(json.dumps(dict(phase=d['phase'],terminal=d.get('terminal',False),child_pid=pid,matching_live_child=live,exit=d.get('exit'))))
