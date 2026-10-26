"""Inventory camera boot configuration and current partition identity."""
from pathlib import Path
import json
import host

code=r'''
from pathlib import Path
import hashlib,json,os,subprocess
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k260-work/boot-id-private.txt').read_bytes()
files={}
for directory in ['/etc/modules-load.d','/etc/modprobe.d','/etc/init.d','/etc/local.d']:
 for p in Path(directory).glob('*'):
  if not p.is_file():continue
  data=p.read_bytes()
  if any(x in data for x in [b'pm8008',b'imx319',b'imx471',b'camss']):files[str(p)]=data.decode()
part={}
for name in ['boot','logdump']:
 q=subprocess.check_output(['findfs','PARTLABEL='+name],text=True).strip()
 assert subprocess.check_output(['lsblk','-ndo','PARTLABEL',q],text=True).strip()==name
 data=Path(q).read_bytes();part[name]=dict(path=q,bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
services=subprocess.check_output(['rc-status','-a'],text=True)
report=dict(stage=267,loader_files=files,partitions=part,services=services,
           running_services=[p.name for p in Path('/run/openrc/started').glob('*')],
           kernel_version=os.uname().version)
print(json.dumps(report))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=40)
(host.PRIVATE/'boot-config-private.json').write_bytes(q.stdout)
d=json.loads(q.stdout)
print(json.dumps(dict(partitions=d['partitions'],loader_files=d['loader_files'],running_services=d['running_services']),indent=2))
