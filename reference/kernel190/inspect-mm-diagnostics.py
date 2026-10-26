import host

code='''from pathlib import Path
import subprocess,json,os,re
root=Path('/var/lib/samurai/k190-mm-diagnostics');assert not root.exists();root.mkdir(mode=0o700)
pid=int(subprocess.check_output(['pidof','ModemManager']).strip())
cmd=Path('/proc')/str(pid)/'cmdline';(root/'daemon-cmdline-private.bin').write_bytes(cmd.read_bytes())
logs={}
for path in [Path('/var/log/messages'),Path('/var/log/ModemManager.log'),Path('/var/log/modemmanager.log')]:
 if path.exists():
  raw=path.read_bytes();(root/(path.name+'-private')).write_bytes(raw)
  lines=raw.decode(errors='replace').splitlines()
  relevant=[line for line in lines if any(word in line.lower() for word in ['assistance','predicted orbit','inject time','location capabilities'])]
  logs[str(path)]=dict(bytes=len(raw),relevant_lines=len(relevant))
  (root/(path.name+'-location-private.txt')).write_text('\\n'.join(relevant))
report=dict(daemon_executable=str((Path('/proc')/str(pid)/'exe').resolve()),
 argv_count=len(cmd.read_bytes().split(b'\\0'))-1,log_files=logs,
 log_directory_names=[p.name for p in Path('/var/log').iterdir()],
 logread_available=subprocess.run(['sh','-c','command -v logread'],capture_output=True).returncode==0)
print(json.dumps(report))
'''
p=host.ssh('python3 -',input=code.encode());(host.PRIVATE/'mm-diagnostics-inspection-private.json').write_bytes(p.stdout);print(p.stdout.decode())
