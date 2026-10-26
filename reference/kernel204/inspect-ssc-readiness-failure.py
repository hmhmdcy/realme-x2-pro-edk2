from pathlib import Path
import json,re,subprocess

root=Path('/var/lib/samurai');out=root/'k204-ssc-failure';assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k204-runtime/boot-id-private.txt').read_bytes()
for p in Path('/var/log').glob('*'):
 if p.is_file() and p.name in ['rc.log','messages','boot.log']:(out/(p.name+'-private-copy')).write_bytes(p.read_bytes())
state=json.loads((out/'state.json').read_text());pid=state.get('pid');alive=pid is not None and Path('/proc/%d'%pid).exists()
findings=[]
for p in out.glob('*private-copy'):
 lines=p.read_text(errors='replace').splitlines()
 for i,l in enumerate(lines):
  if 'samurai-ssc' in l or 'File server exited' in l or 'SSC command failed' in l or 'RuntimeError' in l:
   for row in lines[max(0,i-1):i+2]:
    row=re.sub(r'\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b','<private-boot>',row)
    row=re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b','<private-ip>',row);findings.append(row)
r=dict(stage=204,daemon_pid_still_exists=alive,slpi_attempted=state.get('attempted'),slpi_started=state.get('started'),slpi_stopped=state.get('stopped'),filtered_boot_errors=findings[-20:])
(out/'readiness-inspection.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
