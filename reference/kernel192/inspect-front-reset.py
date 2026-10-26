from pathlib import Path
import os,fcntl,struct,json
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k189r2-reboot-runtime/boot-id-private.txt').read_bytes()
chips=[p for p in Path('/sys/bus/gpio/devices').glob('gpiochip*') if (p/'of_node').exists() and (p/'of_node').resolve().name=='pinctrl@3100000'];assert len(chips)==1
fd=os.open('/dev/'+chips[0].name,os.O_RDONLY|os.O_CLOEXEC);results=[]
try:
 for offset in [12,29,30,23]:
  info=bytearray(256);struct.pack_into('I',info,64,offset);fcntl.ioctl(fd,0xc100b405,info,True)
  result=dict(offset=offset,flags=struct.unpack_from('Q',info,72)[0],consumer=bytes(info[32:64]).split(b'\0')[0].decode())
  if result['consumer']:results.append(result);continue
  req=bytearray(592);struct.pack_into('I',req,0,offset);struct.pack_into('I',req,560,1)
  fcntl.ioctl(fd,0xc250b407,req,True);lfd=struct.unpack_from('i',req,588)[0]
  try:
   data=bytearray(struct.pack('QQ',0,1));fcntl.ioctl(lfd,0xc010b40e,data,True);result['physical_value']=struct.unpack_from('Q',data)[0]&1
  finally:os.close(lfd)
  results.append(result)
finally:os.close(fd)
out=Path('/var/lib/samurai/k192-front-reset');out.mkdir(mode=0o700);(out/'summary.json').write_text(json.dumps(results,indent=2))
print(json.dumps(results))
