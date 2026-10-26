"""Bounded register-address reads at the two documented camera PMIC primaries."""
from pathlib import Path
import array,ctypes,errno,fcntl,json,os,struct,subprocess
os.umask(0o077)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k189r2-reboot-runtime/boot-id-private.txt').read_bytes()
out=Path('/var/lib/samurai/k192-pmic-id-r2');out.mkdir(mode=0o700)
matches=[]
for p in Path('/sys/bus/i2c/devices').glob('i2c-*'):
 node=p/'of_node'
 if not node.exists():node=p/'device/of_node'
 if node.exists() and node.resolve().name=='i2c@890000':matches.append(p)
assert len(matches)==1
adapter=matches[0];number=int(adapter.name.split('-')[1]);assert (Path('/sys/bus/i2c/devices')/f'{number}-0039').exists() and (Path('/sys/bus/i2c/devices')/f'{number}-003a').exists()
for address in [0x04,0x08]:assert not (Path('/sys/bus/i2c/devices')/f'{number}-{address:04x}').exists()
class Msg(ctypes.Structure):_fields_=[('addr',ctypes.c_uint16),('flags',ctypes.c_uint16),('length',ctypes.c_uint16),('buf',ctypes.POINTER(ctypes.c_uint8))]
class Rdwr(ctypes.Structure):_fields_=[('msgs',ctypes.POINTER(Msg)),('nmsgs',ctypes.c_uint32)]
assert os.uname().machine=='aarch64' and ctypes.sizeof(Msg)==16 and ctypes.sizeof(Rdwr)==16
log_before=subprocess.check_output(['dmesg'],text=True);results=[]
fd=os.open('/dev/i2c-'+str(number),os.O_RDWR|os.O_CLOEXEC)
try:
 funcs=array.array('L',[0]);fcntl.ioctl(fd,0x0705,funcs,True);assert funcs[0]&1
 for address in [0x08,0x04]:
  tx=(ctypes.c_uint8*2)(0x01,0x00);rx=(ctypes.c_uint8*6)()
  msgs=(Msg*2)(Msg(address,0,2,tx),Msg(address,1,6,rx));request=Rdwr(msgs,2)
  record=dict(address=address,register=0x0100,read_bytes=6,register_address_bytes=[1,0])
  try:
   count=fcntl.ioctl(fd,0x0707,request);record.update(messages_completed=count,read=list(rx),success=count==2)
  except OSError as error:record.update(success=False,errno=error.errno,error=errno.errorcode.get(error.errno))
  results.append(record)
  (out/'i2c-results.json').write_text(json.dumps(results,indent=2)+'\n')
finally:os.close(fd)
gpio=[]
for p in Path('/sys/bus/gpio/devices').glob('gpiochip*'):
 node=p/'of_node'
 if not node.exists() or 'pmic@4/gpio@c000' not in str(node.resolve()):continue
 fd=os.open('/dev/'+p.name,os.O_RDONLY|os.O_CLOEXEC)
 try:
  chip=bytearray(68);fcntl.ioctl(fd,0x8044b401,chip,True);name,label,lines=struct.unpack('32s32sI',chip)
  for offset in [0,3]:
   data=bytearray(256);struct.pack_into('I',data,64,offset);fcntl.ioctl(fd,0xc100b405,data,True)
   line_name,consumer=data[:32],data[32:64];flags=struct.unpack_from('Q',data,72)[0]
   gpio.append(dict(chip=p.name,label=label.rstrip(b'\0').decode(),offset=offset,pmic_gpio=offset+1,flags=flags,name=line_name.rstrip(b'\0').decode(),consumer=consumer.rstrip(b'\0').decode()))
 finally:os.close(fd)
rails=[]
base=Path('/sys/class/regulator')
for p in base.glob('*'):
 if not (p/'name').exists():continue
 node=p/'of_node'
 if not node.exists():node=p/'device/of_node'
 if (p/'name').read_text().strip()=='smps8' or (node.exists() and node.resolve().name=='smps8'):
  parent=node.resolve() if node.exists() else None
  if parent is not None and not (parent/'qcom,pmic-id').exists():parent=parent.parent
  pmic=(parent/'qcom,pmic-id').read_bytes().rstrip(b'\0').decode() if parent is not None and (parent/'qcom,pmic-id').exists() else None
  if pmic=='c':
   values={}
   for attr in ['name','state','microvolts','num_users','status']:
    try:values[attr]=(p/attr).read_text().strip()
    except OSError:pass
   rails.append(dict(sysfs=p.name,of_path=str(node.resolve()),values=values))
pinconf=[]
for p in Path('/sys/kernel/debug/pinctrl').glob('*/pinconf-pins'):
 if '04' not in p.parent.name and 'pmic@4' not in p.parent.name:continue
 text=p.read_text();(out/(p.parent.name.replace(':','_')+'-pinconf-private.txt')).write_text(text)
 pinconf.extend(line for line in text.splitlines() if line.startswith(('pin 0 ','pin 3 ')))
after=subprocess.check_output(['dmesg'],text=True);(out/'dmesg-after-private.txt').write_text(after)
report=dict(stage=192,bus=number,of_controller='i2c@890000',writes_to_pmic_data_registers=0,gpio_write_requests=0,results=results,reset_lines=gpio,s8c_regulators=rails,
 regulator_sysfs_entries=[dict(name=p.name,label=(p/'name').read_text().strip() if (p/'name').exists() else None) for p in base.glob('*')],pmic_pinconf=pinconf,taint=int(Path('/proc/sys/kernel/tainted').read_text()),fault_delta={k:after.count(v)-log_before.count(v) for k,v in dict(warning='WARNING:',oops='Oops:',slpi_fatal='fatal error received').items()})
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
