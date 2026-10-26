"""Read current FastRPC users and health; no module or service changes."""
from pathlib import Path
import importlib.util
import json

ref = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('usb226', ref.parent / 'kernel226/host.py')
host = importlib.util.module_from_spec(spec)
spec.loader.exec_module(host)
code = r'''
from pathlib import Path
import hashlib,json,os,subprocess
root=Path('/var/lib/samurai');out=root/'k227-baseline'
assert not out.exists();out.mkdir(mode=0o700)
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot==(root/'k226-baseline/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#183 ')
(out/'boot-id-private.txt').write_bytes(boot)
mods=Path('/proc/modules').read_text();(out/'modules-private.txt').write_text(mods)
row=[l.split() for l in mods.splitlines() if l.startswith('fastrpc ')];assert len(row)==1
opens=[]
for proc in Path('/proc').iterdir():
 if not proc.name.isdigit():continue
 try:
  for fd in (proc/'fd').iterdir():
   try:target=os.readlink(fd)
   except (FileNotFoundError,PermissionError):continue
   if target.startswith('/dev/fastrpc-'):
    opens.append(dict(pid=int(proc.name),fd=fd.name,target=target,comm=(proc/'comm').read_text().strip()))
 except (FileNotFoundError,PermissionError):continue
(out/'fastrpc-opens-private.json').write_text(json.dumps(opens,indent=2)+'\n')
for key,args in [('services',['rc-status','--all']),('processes',['ps','aux'])]:
 r=subprocess.run(args,capture_output=True);(out/(key+'-private.txt')).write_bytes(r.stdout+r.stderr)
module=Path('/lib/modules')/os.uname().release/'kernel/drivers/misc/fastrpc.ko'
assert module.is_file()
module_hash=hashlib.sha256(module.read_bytes()).hexdigest()
(out/'fastrpc-module-before-private.ko').write_bytes(module.read_bytes())
rp={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')}
log=subprocess.check_output(['dmesg']);(out/'dmesg-private.txt').write_bytes(log)
faults={k:log.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()}
taint=int(Path('/proc/sys/kernel/tainted').read_text())
assert not taint and not any(faults.values()) and rp==dict(adsp='running',slpi='running',modem='running')
report=dict(stage=227,same219_boot=True,kernel_build=183,module_refcount=int(row[0][2]),
 fastrpc_open_fds=len(opens),fastrpc_module_sha256=module_hash,fastrpc_module_bytes=module.stat().st_size,
 remoteprocs=rp,taint=taint,faults=faults,no_service_module_or_power_change=True)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
result = host.ssh('python3 -', input=code.encode(), timeout=40)
private = Path('/mnt/e/edk2-samurai-out/kernel227')
(private / 'device-baseline-host-private.log').write_bytes(result.stdout + result.stderr)
report = json.loads(result.stdout)
(ref / 'device-baseline-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
