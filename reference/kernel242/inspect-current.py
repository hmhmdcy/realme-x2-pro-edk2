"""Fresh read-only boot, Android-availability and capture-backend inventory."""
from pathlib import Path
import importlib.util, json

R = Path(__file__).resolve().parent
P = Path('/mnt/e/edk2-samurai-out/kernel242')
P.mkdir(mode=0o700, exist_ok=True)
spec = importlib.util.spec_from_file_location('host', R.parent/'kernel240/host.py')
host = importlib.util.module_from_spec(spec); spec.loader.exec_module(host)
code = r'''
from pathlib import Path
import json, subprocess, hashlib, os
def run(args):
    x=subprocess.run(args,capture_output=True,timeout=25)
    return dict(rc=x.returncode,stdout=x.stdout.decode(errors='replace'),stderr=x.stderr.decode(errors='replace'))
r=Path('/var/lib/samurai')
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()
report=dict(stage=242,current236_boot=boot==(r/'k236-runtime/boot-id-private.txt').read_bytes(),
 kernel=run(['uname','-r'])['stdout'].strip(),taint=int(Path('/proc/sys/kernel/tainted').read_text()),
 root=run(['findmnt','-n','-o','SOURCE,FSTYPE','/'])['stdout'].strip(),
 android_init_present=Path('/system/bin/init').exists(),android_getprop_present=Path('/system/bin/getprop').exists(),
 remoteprocs=[dict(name=(x/'name').read_text().strip(),state=(x/'state').read_text().strip()) for x in Path('/sys/class/remoteproc').glob('remoteproc*')],
 trace_candidates=[str(x) for x in Path('/sys/kernel/tracing/events').glob('*') if any(y in x.name for y in ['qrtr','qmi','remoteproc','regulator','clk'])],readonly=True)
private=dict(report=report,mounts=run(['findmnt','-J']),partitions=run(['lsblk','-J','-b','-o','NAME,SIZE,FSTYPE,PARTLABEL,MOUNTPOINTS']),
 cmdline=Path('/proc/cmdline').read_text(),processes=run(['ps','-eo','pid,comm,args']),
 misc_files=[str(x) for x in r.glob('*android*')],config=run(['zcat','/proc/config.gz']))
print(json.dumps(private))
'''
result=host.ssh('python3 -',input=code.encode(),timeout=100)
(P/'current-inventory-private.json').write_bytes(result.stdout)
private=json.loads(result.stdout)
(R/'baseline-validation.json').write_text(json.dumps(private['report'],indent=2)+'\n')
print(json.dumps(private['report']))
