from pathlib import Path
import json,shlex
import host
HERE=Path(__file__).resolve().parent
code='''
from pathlib import Path
import fcntl,hashlib,json,os,struct,subprocess
nodes=[p for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().startswith('s5kgw1 ')]
assert len(nodes)==1
fd=os.open('/dev/'+nodes[0].name,os.O_RDONLY|os.O_CLOEXEC)
try:
 value=bytearray(struct.pack('<Ii',0x009f0903,0));fcntl.ioctl(fd,0xc008561b,value,True);pattern=struct.unpack('<Ii',value)[1]
finally:os.close(fd)
target=Path(subprocess.check_output(['modinfo','-n','s5kgw1'],text=True).strip()).resolve()
services={}
for name in ['pipewire','wireplumber']:
 rows=[]
 for p in Path('/proc').glob('[0-9]*'):
  try:
   if (p/'comm').read_text().strip()==name:rows.append(dict(pid=int(p.name),uid=p.stat().st_uid))
  except (FileNotFoundError,ProcessLookupError):pass
 services[name]=rows
report=dict(stage=325,test_pattern=pattern,module_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),loaded_note_sha256=hashlib.sha256(Path('/sys/module/s5kgw1/notes/.note.gnu.build-id').read_bytes()).hexdigest(),services=services,
 platforms={n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip() for n in ['acb3000.camss','ac4a000.cci','ac4b000.cci']},taint=int(Path('/proc/sys/kernel/tainted').read_text()))
print(json.dumps(report))
'''
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=20);d=json.loads(q.stdout)
build=json.loads((HERE/'kernel-build-validation.json').read_text());proof=json.loads((host.PRIVATE/'install-r3-proof.json').read_text())
d['passed']=d['test_pattern']==0 and d['module_sha256']==build['module_sha256'] and d['loaded_note_sha256']==proof['module_note_sha256'] and not d['taint'] and all(v=='suspended' for v in d['platforms'].values()) and all(len(v)==1 and v[0]['uid']==10000 for v in d['services'].values())
(HERE/'final-state-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2));assert d['passed']
