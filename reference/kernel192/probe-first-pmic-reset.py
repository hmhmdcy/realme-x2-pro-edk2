"""Release only PM8150L GPIO1 temporarily; preserve the already-addressed second PMIC."""
from pathlib import Path
import ctypes,errno,fcntl,json,os,signal,struct,time
os.umask(0o077);out=Path('/var/lib/samurai/k192-pmic-a-release');out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k189r2-reboot-runtime/boot-id-private.txt').read_bytes()
prior=json.loads(Path('/var/lib/samurai/k192-reset-levels/summary.json').read_text());assert prior['levels'][0]['physical_level']==0 and prior['levels'][1]['physical_level']==1
chips=[p for p in Path('/sys/bus/gpio/devices').glob('gpiochip*') if (p/'of_node').exists() and str((p/'of_node').resolve()).endswith('/pmic@4/gpio@c000')];assert len(chips)==1
chip=chips[0];gpiofd=os.open('/dev/'+chip.name,os.O_RDONLY|os.O_CLOEXEC);linefd=None
buspath=Path('/sys/bus/i2c/devices/i2c-1');assert (buspath/'of_node').resolve().name=='i2c@890000'
assert all(not Path('/sys/bus/i2c/devices/1-'+f'{a:04x}').exists() for a in [4,5,8,9])
i2cfd=os.open('/dev/i2c-1',os.O_RDWR|os.O_CLOEXEC)
class Msg(ctypes.Structure):_fields_=[('addr',ctypes.c_uint16),('flags',ctypes.c_uint16),('length',ctypes.c_uint16),('buf',ctypes.POINTER(ctypes.c_uint8))]
class Rdwr(ctypes.Structure):_fields_=[('msgs',ctypes.POINTER(Msg)),('nmsgs',ctypes.c_uint32)]
def read(address,reg,count):
 tx=(ctypes.c_uint8*2)(reg>>8,reg&255);rx=(ctypes.c_uint8*count)();msgs=(Msg*2)(Msg(address,0,2,tx),Msg(address,1,count,rx));request=Rdwr(msgs,2)
 try:
  completed=fcntl.ioctl(i2cfd,0x0707,request);return dict(address=address,register=reg,data=list(rx),messages=completed,success=completed==2)
 except OSError as error:return dict(address=address,register=reg,success=False,errno=error.errno,error=errno.errorcode.get(error.errno))
def snapshot(primary):
 result=dict(identity=read(primary,0x0100,6),sid_config=read(primary,0x0644,1),chip_enable=read(primary,0x0950,1),ldos=[])
 if not result['identity']['success']:return result
 for i in range(7):
  base=0x4000+0x100*i
  result['ldos'].append(dict(index=i+1,status=read(primary+1,base+8,1),voltage_mv=read(primary+1,base+0x40,2),enable=read(primary+1,base+0x46,1)))
 return result
report=dict(stage=192,reset_line=1,second_reset_line_changed=False,pmic_register_data_writes=0,levels_requested=[],before_second=snapshot(4))
assert report['before_second']['identity']['success'] and report['before_second']['identity']['data'][4:]==[0x51,0x2c]
def save():(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
def interrupted(signum,frame):raise RuntimeError('Interrupted while owning camera reset')
for sig in [signal.SIGHUP,signal.SIGTERM,signal.SIGINT]:signal.signal(sig,interrupted)
def get_value():
 value=bytearray(struct.pack('QQ',0,1));fcntl.ioctl(linefd,0xc010b40e,value,True);return struct.unpack('QQ',value)[0]&1
def set_value(value):
 data=bytearray(struct.pack('QQ',value,1));fcntl.ioctl(linefd,0xc010b40f,data,True);report['levels_requested'].append(value)
try:
 info=bytearray(256);struct.pack_into('I',info,64,0);fcntl.ioctl(gpiofd,0xc100b405,info,True);assert struct.unpack_from('Q',info,72)[0]==8
 # Request with the original physical low level first, then release reset.
 req=bytearray(592);struct.pack_into('I',req,0,0);req[256:256+15]=b'samurai-pmic-id\0';struct.pack_into('Q',req,288,8)
 struct.pack_into('I',req,296,1);struct.pack_into('I',req,320,2);struct.pack_into('Q',req,328,0);struct.pack_into('Q',req,336,1);struct.pack_into('I',req,560,1)
 fcntl.ioctl(gpiofd,0xc250b407,req,True);linefd=struct.unpack_from('i',req,588)[0];assert linefd>=0 and get_value()==0
 set_value(1);assert get_value()==1;save();time.sleep(.010)
 report['during_first']=snapshot(8);save()
 report['during_second']=snapshot(4);save()
finally:
 if linefd is not None:
  set_value(0);report['restored_first_level']=get_value();os.close(linefd)
 os.close(gpiofd)
 report['after_first_identity']=read(8,0x0100,6);report['after_second']=snapshot(4);os.close(i2cfd);save()
print(json.dumps(dict(stage=192,first_identity=report.get('during_first',{}).get('identity'),restored_first_level=report.get('restored_first_level'),after_first=report['after_first_identity'],second_identity_preserved=report['before_second']['identity']==report['after_second']['identity'],pmic_data_writes=0)))
assert report.get('restored_first_level')==0 and report['before_second']==report['after_second']
