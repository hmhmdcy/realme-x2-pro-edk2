"""Inspect user-supplied ROM offline. No installer or image is executed."""
from pathlib import Path
import ctypes,ctypes.util,gzip,hashlib,importlib.util,json,re,struct,zipfile
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel242')
Z=Path('/mnt/c/Users/cy122/Downloads/crDroidAndroid-16.0-20251217-samurai-v12.4.zip')
O=P/'android-rom';O.mkdir(mode=0o700,exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  while b:=f.read(4*1024*1024):h.update(b)
 return h.hexdigest()
def boot_info(data,label):
 assert data[:8]==b'ANDROID!'
 kernel,ka,rd,ra,second,sa,tags,page,version=struct.unpack_from('<9I',data,8)
 assert page in [2048,4096,8192,16384] and version in [0,1,2]
 off=page+((kernel+page-1)//page)*page
 ram=data[off:off+rd]
 (O/(label+'-ramdisk-private.bin')).write_bytes(ram)
 if ram.startswith(b'\x1f\x8b'):decomp=gzip.decompress(ram)
 elif ram.startswith(bytes.fromhex('02214c18')):
  lib=ctypes.CDLL(ctypes.util.find_library('lz4'))
  fn=lib.LZ4_decompress_safe;fn.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int,ctypes.c_int];fn.restype=ctypes.c_int
  pos=4;parts=[]
  while pos<len(ram):
   n=struct.unpack_from('<I',ram,pos)[0];pos+=4
   if n==0:break
   assert 0<n<=len(ram)-pos
   compressed=ram[pos:pos+n];pos+=n;buf=ctypes.create_string_buffer(8*1024*1024)
   length=fn(compressed,buf,n,len(buf));assert length>0
   parts.append(buf.raw[:length])
  assert pos==len(ram);decomp=b''.join(parts)
 else:decomp=ram
 (O/(label+'-ramdisk-unpacked-private.bin')).write_bytes(decomp)
 files={};i=0
 while i+110<=len(decomp):
  header=decomp[i:i+110]
  if header[:6] not in [b'070701',b'070702']:break
  fields=[int(header[6+j*8:14+j*8],16) for j in range(13)]
  size,namesize=fields[6],fields[11]
  name=decomp[i+110:i+110+namesize-1].decode(errors='replace')
  start=(i+110+namesize+3)&~3
  if name=='TRAILER!!!':break
  files[name]=dict(bytes=size,mode=fields[1],sha256=hashlib.sha256(decomp[start:start+size]).hexdigest())
  if re.search(r'fstab|(^|/)init[^/]*\.rc$|prop$',name) and size<2*1024*1024:
   dst=O/(label+'-ramdisk-selected')/name
   assert dst.resolve().is_relative_to((O/(label+'-ramdisk-selected')).resolve())
   dst.parent.mkdir(mode=0o700,parents=True,exist_ok=True);dst.write_bytes(decomp[start:start+size])
  i=(start+size+3)&~3
 (O/(label+'-cpio-manifest-private.json')).write_text(json.dumps(files,indent=2)+'\n')
 return dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),kernel_bytes=kernel,ramdisk_bytes=rd,
  header_version=version,page_size=page,ramdisk_cpio_files=len(files),ramdisk_parse_complete='TRAILER!!!'==name if files else False)
with zipfile.ZipFile(Z) as z:
 names=z.namelist();assert len(names)==len(set(names))
 selected={}
 for name in ['META-INF/com/android/metadata','META-INF/com/google/android/updater-script','system.transfer.list','vendor.transfer.list','odm.transfer.list']:
  selected[name]=z.read(name).decode();dst=O/Path(name).name;dst.write_text(selected[name])
 for name in ['boot.img','recovery.img','dtbo.img','vbmeta.img']:
  (O/name).write_bytes(z.read(name))
 boot=boot_info((O/'boot.img').read_bytes(),'rom')
 stock=boot_info(Path('/mnt/e/edk2-samurai-out/backup/boot_stock_RMX1931.img').read_bytes(),'stock-backup')
 updater=selected['META-INF/com/google/android/updater-script']
 meta=dict(line.split('=',1) for line in selected['META-INF/com/android/metadata'].splitlines() if '=' in line)
 private=dict(zip_manifest=[dict(name=x.filename,bytes=x.file_size,crc32=f'{x.CRC:08x}') for x in z.infolist()],metadata=meta,updater_script=updater,
  boot=boot,stock_boot=stock,zip_sha256=sha(Z))
 report=dict(stage=242,rom_filename=Z.name,zip_bytes=Z.stat().st_size,metadata_device=meta.get('pre-device'),ota_type=meta.get('ota-type'),
  full_partition_payloads=[p for p in ['system','vendor','odm'] if p+'.new.dat.br' in names],
  boot_present='boot.img' in names,recovery_present='recovery.img' in names,modem_firmware_partition_payload_present=any(re.search(r'(^|/)(NON-HLOS\.bin|modem\.img|modem\.new\.dat|firmware-update/)',n,re.I) for n in names),
  userdata_backup_present=any(re.search(r'(^|/)(userdata|data)\.(img|new\.dat|win)',n) for n in names),
  boot_header_version=boot['header_version'],boot_ramdisk_files=boot['ramdisk_cpio_files'],
  boot_matches_old_stock_backup=boot['sha256']==stock['sha256'],brotli_python_available=importlib.util.find_spec('brotli') is not None,
  installer_not_executed=True,no_phone_changes=True)
 private['report']=report
 (P/'android-rom-inspection-private.json').write_text(json.dumps(private,indent=2)+'\n')
 (R/'android-rom-validation.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report))
