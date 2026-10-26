"""Read current module identity, standard controls and selection support."""
from pathlib import Path
import hashlib,json,shlex
import host
R=Path(__file__).parent
code=r'''
from pathlib import Path
import errno,fcntl,hashlib,json,os,struct,subprocess
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k260-work/boot-id-private.txt').read_bytes()
proof=json.loads((r/'k265-package-transaction/summary.json').read_text())
for name,digest in proof['payload_sha256'].items():assert hashlib.sha256((Path('/')/name).read_bytes()).hexdigest()==digest
services=json.loads((r/'k265-services-current-private.json').read_text());assert not services['spa_candidate_active']
for i in services['new_processes']:
 p=Path('/proc',str(i['pid']));assert (p/'stat').read_text().rsplit(')',1)[1].split()[19]==i['start_ticks']
devices=['7-0010','9-0010'];items={}
for device in devices:
 p=Path('/sys/bus/i2c/devices',device);assert (p/'power/runtime_status').read_text().strip()=='suspended'
 node=next(n for n in Path('/sys/class/video4linux').glob('v4l-subdev*') if (n/'device').resolve()==p.resolve())
 controls=subprocess.check_output(['v4l2-ctl','-d','/dev/'+node.name,'--list-ctrls']).decode();selection={}
 fd=os.open('/dev/'+node.name,os.O_RDWR|os.O_CLOEXEC)
 try:
  for name,target in [('crop',0),('default',1),('bounds',2),('native',3),('compose',256)]:
   data=bytearray(64);struct.pack_into('IIII',data,0,1,0,target,0)
   try:fcntl.ioctl(fd,0xc040563d,data,True);selection[name]=dict(zip(['left','top','width','height'],struct.unpack_from('iiII',data,16)))
   except OSError as e:selection[name]=dict(errno=e.errno)
 finally:os.close(fd)
 of=(p/'of_node').resolve();properties={n:int.from_bytes((of/n).read_bytes(),'big') for n in ['orientation','rotation'] if (of/n).exists()}
 items[device]=dict(entity=(node/'name').read_text().strip(),controls=controls,selection=selection,firmware_properties=properties)
tree=Path('/usr/lib/modules')/os.uname().release;module=tree/'kernel/drivers/media/i2c/imx319.ko';data=module.read_bytes()
offset=struct.unpack_from('<Q',data,40)[0];size,count,index=struct.unpack_from('<HHH',data,58);sections=[struct.unpack_from('<IIQQQQIIQQ',data,offset+i*size) for i in range(count)];strings=data[sections[index][4]:sections[index][4]+sections[index][5]]
notes=[data[s[4]:s[4]+s[5]] for s in sections if strings[s[0]:].split(b'\0',1)[0]==b'.note.gnu.build-id'];assert len(notes)==1 and notes[0]==Path('/sys/module/imx319/notes/.note.gnu.build-id').read_bytes()
report=dict(stage=266,current_boot_verified=True,common_r3_payloads_verified=True,services=services['new_processes'],sensors=items,imx319_disk_and_loaded_note_match=True,imx319_sha256=hashlib.sha256(data).hexdigest(),module_release=os.uname().release,taint=int(Path('/proc/sys/kernel/tainted').read_text()),no_frames_requested=True)
assert report['taint']==0;print(json.dumps(report))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=25);(host.PRIVATE/'baseline-private.json').write_bytes(q.stdout);d=json.loads(q.stdout);(R/'baseline-validation.json').write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps({k:v for k,v in d.items() if k!='sensors'},indent=2));print(json.dumps({k:{x:v[x] for x in ['entity','selection','firmware_properties']} for k,v in d['sensors'].items()},indent=2))

