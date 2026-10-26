from pathlib import Path
import json,subprocess
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
procs=[]
for p in Path('/sys/class/remoteproc').glob('*'):
 procs.append(dict(path=str(p.resolve()),name=(p/'name').read_text().strip(),state=(p/'state').read_text().strip(),firmware=(p/'firmware').read_text().strip()))
private={}
for name in ['tftp','rmtfs','pd-mapper','qrtr-ns']:
 private[name]=[]
 for p in Path('/proc').glob('[0-9]*/cmdline'):
  try:args=p.read_bytes().split(b'\0')
  except OSError:continue
  if args and Path(args[0].decode(errors='replace')).name==name:private[name].append(dict(pid=int(p.parent.name),argv=[x.decode(errors='replace') for x in args if x]))
report=dict(stage=244,remoteprocs=procs,file_service_process_counts={k:len(v) for k,v in private.items()},same236_boot=True)
print(json.dumps({'report':report,'private':{'services':private,'mountinfo':Path('/proc/self/mountinfo').read_text(),'qrtr':subprocess.check_output(['qrtr-lookup']).decode(),'dmesg':subprocess.check_output(['dmesg']).decode()}}))
