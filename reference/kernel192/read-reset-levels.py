"""GPIO v2 as-is request: read levels without requesting direction, bias, or drive changes."""
from pathlib import Path
import fcntl,json,os,struct
os.umask(0o077);out=Path('/var/lib/samurai/k192-reset-levels');out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k189r2-reboot-runtime/boot-id-private.txt').read_bytes()
chips=[p for p in Path('/sys/bus/gpio/devices').glob('gpiochip*') if (p/'of_node').exists() and str((p/'of_node').resolve()).endswith('/pmic@4/gpio@c000')];assert len(chips)==1
chip=chips[0];fd=os.open('/dev/'+chip.name,os.O_RDONLY|os.O_CLOEXEC);linefd=None
def info(offset):
 buf=bytearray(256);struct.pack_into('I',buf,64,offset);fcntl.ioctl(fd,0xc100b405,buf,True)
 return dict(offset=offset,flags=struct.unpack_from('Q',buf,72)[0],consumer=bytes(buf[32:64]).rstrip(b'\0').decode())
before=[info(n) for n in [0,3]];assert all(not (r['flags']&1) for r in before)
try:
 req=bytearray(592);struct.pack_into('II',req,0,0,3);req[256:256+19]=b'samurai-camera-read'
 struct.pack_into('Q',req,288,0);struct.pack_into('I',req,560,2)
 fcntl.ioctl(fd,0xc250b407,req,True);linefd=struct.unpack_from('i',req,588)[0];assert linefd>=0
 values=bytearray(struct.pack('QQ',0,3));fcntl.ioctl(linefd,0xc010b40e,values,True);bits,mask=struct.unpack('QQ',values)
 levels=[dict(pmic_gpio=1,offset=0,physical_level=int(bool(bits&1))),dict(pmic_gpio=4,offset=3,physical_level=int(bool(bits&2)))]
 (out/'levels.json').write_text(json.dumps(levels,indent=2))
finally:
 if linefd is not None:os.close(linefd)
after=[info(n) for n in [0,3]];os.close(fd);assert after==before
report=dict(stage=192,chip=chip.name,as_is_request_flags=0,requested_line_offsets=[0,3],levels=levels,line_info_before=before,line_info_after=after,configuration_unchanged=True)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
