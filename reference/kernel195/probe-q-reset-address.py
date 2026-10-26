"""One PM8008 Q reset with camera outputs off, followed by original address/state restoration."""
from pathlib import Path
import ctypes,errno,fcntl,json,os,signal,struct,time,subprocess
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k195-q-reset';out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k195-baseline/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='512'
assert not Path('/sys/module/samurai_cci_bringup').exists() and not Path('/sys/module/samurai_front_identify').exists()
adapter=Path('/sys/bus/i2c/devices/i2c-1');assert (adapter/'of_node').resolve().name=='i2c@890000'
assert all(not Path('/sys/bus/i2c/devices/1-'+f'{a:04x}').exists() for a in [4,5,8,9])
chips=[p for p in Path('/sys/bus/gpio/devices').glob('gpiochip*') if (p/'of_node').exists() and str((p/'of_node').resolve()).endswith('/pmic@4/gpio@c000')];assert len(chips)==1
gfd=os.open('/dev/'+chips[0].name,os.O_RDONLY|os.O_CLOEXEC);ifd=os.open('/dev/i2c-1',os.O_RDWR|os.O_CLOEXEC);line=None;attempted_sid=False
class Msg(ctypes.Structure):_fields_=[('addr',ctypes.c_uint16),('flags',ctypes.c_uint16),('length',ctypes.c_uint16),('buf',ctypes.POINTER(ctypes.c_uint8))]
class Rdwr(ctypes.Structure):_fields_=[('msgs',ctypes.POINTER(Msg)),('nmsgs',ctypes.c_uint32)]
def read(address,reg,count):
 tx=(ctypes.c_uint8*2)(reg>>8,reg&255);rx=(ctypes.c_uint8*count)();messages=(Msg*2)(Msg(address,0,2,tx),Msg(address,1,count,rx));request=Rdwr(messages,2)
 try:
  result=fcntl.ioctl(ifd,0x0707,request);return dict(success=result==2,data=list(rx),messages=result)
 except OSError as error:return dict(success=False,errno=error.errno)
def write(address,reg,data):
 tx=(ctypes.c_uint8*(2+len(data)))(reg>>8,reg&255,*data);messages=(Msg*1)(Msg(address,0,len(tx),tx));request=Rdwr(messages,1)
 try:
  result=fcntl.ioctl(ifd,0x0707,request);return dict(address=address,register=reg,data=data,success=result==1,messages=result)
 except OSError as error:return dict(address=address,register=reg,data=data,success=False,errno=error.errno)
def snapshot(primary):
 identity=read(primary,0x100,6);result=dict(identity=identity)
 if not identity['success']:return result
 result.update(sid=read(primary,0x644,1),chip_enable=read(primary,0x950,1),ldos=[])
 for i in range(7):
  base=0x4000+i*0x100;result['ldos'].append(dict(index=i+1,status=read(primary+1,base+8,1),vset=read(primary+1,base+0x40,2),enable=read(primary+1,base+0x46,1),mode=read(primary+1,base+0x45,1),step=read(primary+1,base+0x3b,1),pull_down=read(primary+1,base+0xa0,1)))
 return result
def level(fd):
 b=bytearray(struct.pack('QQ',0,1));fcntl.ioctl(fd,0xc010b40e,b,True);return struct.unpack_from('Q',b)[0]&1
def request(offset,flags):
 req=bytearray(592);struct.pack_into('I',req,0,offset);struct.pack_into('Q',req,288,flags);struct.pack_into('I',req,560,1)
 if flags:
  struct.pack_into('I',req,296,1);struct.pack_into('I',req,320,2);struct.pack_into('Q',req,328,1);struct.pack_into('Q',req,336,1)
 fcntl.ioctl(gfd,0xc250b407,req,True);return struct.unpack_from('i',req,588)[0]
def sample(offset):
 info=bytearray(256);struct.pack_into('I',info,64,offset);fcntl.ioctl(gfd,0xc100b405,info,True);assert struct.unpack_from('Q',info,72)[0]==8 and not bytes(info[32:64]).rstrip(b'\0')
 fd=request(offset,0)
 try:return level(fd)
 finally:os.close(fd)
report=dict(stage=195,gpio1_before=sample(0),gpio4_before=sample(3),before=snapshot(4),address8_before=read(8,0x100,6),writes=[],reset_levels=[])
assert report['gpio1_before']==0 and report['gpio4_before']==1 and report['before']['identity']['data']==[0,0,0,1,0x51,0x2c]
assert not report['address8_before']['success'] and report['before']['sid']['data']==[1] and report['before']['chip_enable']['data']==[1]
assert all(r['enable']['data']==[0] and all(v.get('success',False) for k,v in r.items() if k!='index') for r in report['before']['ldos'])
log_before=subprocess.check_output(['dmesg']);(out/'dmesg-before-private.txt').write_bytes(log_before)
def save():(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
def set_level(value):
 b=bytearray(struct.pack('QQ',value,1));fcntl.ioctl(line,0xc010b40f,b,True);assert level(line)==value;report['reset_levels'].append(value);save()
def interrupt(signum,frame):raise RuntimeError('Interrupted PMIC address experiment; restore original state')
for sig in [signal.SIGTERM,signal.SIGINT,signal.SIGHUP]:signal.signal(sig,interrupt)
save()
try:
 line=request(3,8);assert level(line)==1
 set_level(0);time.sleep(.010);set_level(1);time.sleep(.010)
 report['after_reset_at4']=snapshot(4);report['after_reset_at8']=snapshot(8);save()
finally:
 if line is not None:
  if level(line)!=1:set_level(1);time.sleep(.010)
  at4=read(4,0x100,6);at8=read(8,0x100,6);report['restore_initial_addresses']=dict(at4=at4,at8=at8);save()
  if not at4['success'] and at8.get('data')==[0,0,0,1,0x51,0x2c]:
   attempted_sid=True;report['writes'].append(write(8,0x644,[1]));save();time.sleep(.010)
  current=snapshot(4);report['before_register_restore']=current;save()
  if current['identity'].get('data')==report['before']['identity']['data']:
   if current['chip_enable']['data']!=report['before']['chip_enable']['data']:report['writes'].append(write(4,0x950,report['before']['chip_enable']['data']))
   for old,new in zip(report['before']['ldos'],current['ldos']):
    base=0x4000+(old['index']-1)*0x100
    for name,offset in [('enable',0x46),('vset',0x40),('mode',0x45),('step',0x3b),('pull_down',0xa0)]:
     if new[name]['data']!=old[name]['data']:report['writes'].append(write(5,base+offset,old[name]['data']));save()
  report['after_restore']=snapshot(4);report['address8_after']=read(8,0x100,6);report['gpio4_at_release']=level(line);os.close(line)
 report['gpio1_after']=sample(0);report['gpio4_after']=sample(3);os.close(gfd);os.close(ifd);save()
after_log=subprocess.check_output(['dmesg']);(out/'dmesg-after-private.txt').write_bytes(after_log)
report['fault_delta']={k:after_log.count(v)-log_before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()};save()
assert report['after_restore']==report['before'] and not report['address8_after']['success'] and report['gpio1_after']==0 and report['gpio4_after']==1 and all(v==0 for v in report['fault_delta'].values())
print(json.dumps(dict(stage=195,reset_pulses=1,after_reset_address4=report.get('after_reset_at4',{}).get('identity'),after_reset_address8=report.get('after_reset_at8',{}).get('identity'),after_reset_sid=report.get('after_reset_at8',{}).get('sid'),after_reset_chip_enable=report.get('after_reset_at8',{}).get('chip_enable'),writes=report['writes'],original_address_and_sampled_registers_restored=True,gpio1_unchanged=True,gpio4_restored=True,fault_delta=report['fault_delta'])))
