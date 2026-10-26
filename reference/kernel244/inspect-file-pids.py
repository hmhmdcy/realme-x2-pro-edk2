from pathlib import Path
import json,os
rows={};private={}
for name in ['tftp','rmtfs','pd-mapper']:
 p=Path('/run/samurai-wifi')/(name+'.pid')
 if not p.exists():rows[name]=dict(pid_file_present=False);continue
 pid=int(p.read_text());process=Path('/proc')/str(pid);assert process.exists();args=process.joinpath('cmdline').read_bytes().split(b'\0');private[name]=dict(pid=pid,argv=[x.decode(errors='replace') for x in args if x],exe=str(process.joinpath('exe').resolve()))
 rows[name]=dict(pid_file_present=True,alive=True,executable_name=Path(private[name]['exe']).name)
print(json.dumps({'report':dict(stage=244,pid_files=rows),'private':private}))
