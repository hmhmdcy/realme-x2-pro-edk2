from pathlib import Path
import json,re,subprocess

root=Path('/var/lib/samurai');out=root/'k204-ssc-failure';assert not out.exists();out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k204-runtime/boot-id-private.txt').read_bytes()
source=Path('/usr/sbin/samurai-ssc');(out/'service-source-private.py').write_bytes(source.read_bytes())
logs={}
for p in Path('/run/samurai-ssc').iterdir():
 if not p.is_file() or p.is_symlink():continue
 raw=p.read_bytes();(out/p.name).write_bytes(raw)
 if p.suffix in ['.log','.json']:
  text=raw.decode(errors='replace');lines=[l for l in text.splitlines() if re.search(r'fail|error|timeout|stop|state|start|boot|ready|offline',l,re.I)]
  lines=[re.sub(r'\b[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\b','<private-boot>',re.sub(r'\b[0-9a-fA-F]{16,}\b','<private-id>',l)) for l in lines]
  logs[p.name]=lines[-16:]
r=dict(stage=204,no_service_restart=True,slpi_state=Path('/sys/class/remoteproc/remoteproc0/state').read_text().strip(),service_files=[p.name for p in out.iterdir()],filtered_error_lines=logs)
(out/'summary.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
