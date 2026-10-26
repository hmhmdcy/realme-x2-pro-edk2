from pathlib import Path
import fcntl,json,mmap,os,struct
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k200-runtime/boot-id-private.txt').read_bytes()
node=Path('/sys/firmware/devicetree/base/soc@0/pinctrl@3100000');chips=[p for p in Path('/sys/bus/gpio/devices').glob('gpiochip*') if (p/'of_node').exists() and (p/'of_node').resolve()==node];assert len(chips)==1
fd=os.open('/dev/'+chips[0].name,os.O_RDONLY);mem=os.open('/dev/mem',os.O_RDONLY|os.O_SYNC)
r=[]
for pin,addr in [(12,0x0390c000),(15,0x0390f000),(29,0x0351d000)]:
 b=bytearray(256);struct.pack_into('I',b,64,pin);fcntl.ioctl(fd,0xc100b405,b,True)
 with mmap.mmap(mem,4096,flags=mmap.MAP_SHARED,prot=mmap.PROT_READ,offset=addr) as m:ctl=struct.unpack_from('<I',m,0)[0]
 r.append(dict(pin=pin,ctl=ctl,flags=struct.unpack_from('Q',b,72)[0],claimed=bool(bytes(b[32:64]).rstrip(b'\0'))))
os.close(fd);os.close(mem);print(json.dumps(r))
