"""Read only a verified dedicated firmware DDR window; never start the A5."""
from pathlib import Path
import hashlib,json,shlex,struct
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;image=P.parent/'kernel352/CAMERA_ICP.elf-private';raw=image.read_bytes()
phoff=struct.unpack_from('<I',raw,28)[0];stride,count=struct.unpack_from('<HH',raw,42)
segments=[struct.unpack_from('<8I',raw,phoff+i*stride) for i in range(count)]
first=next(s for s in segments if s[0]==1 and s[2]==0);expected=hashlib.sha256(raw[first[1]:first[1]+4096]).hexdigest()
code=r'''
from pathlib import Path
import base64,hashlib,json,mmap,os
base=Path('/sys/firmware/devicetree/base');memory=base/'reserved-memory/memory@9ab00000'
assert (memory/'reg').read_bytes()==bytes.fromhex('000000009ab000000000000000500000') and (memory/'no-map').exists()
assert (base/'soc@0/icp@ac10000/status').read_bytes()==b'disabled\0'
for name in ['qcom_camss_icp_a5_core','camss_icp_a5_boot_test']:assert not Path('/sys/module',name).exists()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert os.sysconf('SC_PAGE_SIZE')==4096
physical=0x9ab00000;pages={}
fd=os.open('/dev/mem',os.O_RDONLY|os.O_SYNC)
try:
 def page(offset):
  assert offset%4096==0 and 0<=offset<=0x500000-4096
  with mmap.mmap(fd,4096,flags=mmap.MAP_SHARED,prot=mmap.PROT_READ,offset=physical+offset) as view:return bytes(view)
 data=page(0);pages['000000']=base64.b64encode(data).decode();matched=hashlib.sha256(data).hexdigest()==expected
 if matched:
  for offset in [0x100000,0x109000,0x11c000,0x11e000,0x120000,0x126000]:pages[f'{offset:06x}']=base64.b64encode(page(offset)).decode()
finally:os.close(fd)
print(json.dumps(dict(code_page_matches_known_firmware=matched,pages_b64=pages,taint_after=int(Path('/proc/sys/kernel/tainted').read_text()),firmware_cpu_started=False,physical_write_performed=False)))
'''
marker=P/'retained-firmware-ddr-private.json';assert not marker.exists(),'Inspect prior snapshot rather than overwriting it'
q=host.ssh('python3 -c '+shlex.quote('expected='+repr(expected)+'\n'+code),timeout=25);marker.write_bytes(q.stdout);d=json.loads(q.stdout)
import base64
for name,value in d['pages_b64'].items():(P/('retained-'+name+'-private.bin')).write_bytes(base64.b64decode(value))
values={}
if d['code_page_matches_known_firmware']:
 b=base64.b64decode(d['pages_b64']['109000'])
 values={name:struct.unpack_from('<I',b,offset-0x109000)[0] for name,offset in [('rex_abort_far',0x1099a0),('rex_abort_fsr',0x1099a4),('rex_exception_type',0x1099a8)]}
report=dict(stage=368,code_page_matches_known_firmware=d['code_page_matches_known_firmware'],pages_read=len(d['pages_b64']),
    exception_state=values,physical_write_performed=False,firmware_cpu_started=False,taint_after=d['taint_after'],
    residual_state_provenance_not_yet_confirmed=True,raw_pages_private_only=True)
(HERE/'retained-firmware-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
