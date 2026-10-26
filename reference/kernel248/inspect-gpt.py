from pathlib import Path
import json,struct,zlib
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k247-runtime/boot-id-private.txt').read_bytes();out=[]
for name in ['sda','sdb','sdc','sdd','sde','sdf']:
 p=Path('/sys/class/block')/name;size=int((p/'size').read_text())*512;lb=int((p/'queue/logical_block_size').read_text());row=dict(lun=name,bytes=size,logical_block_size=lb)
 with open('/dev/'+name,'rb',buffering=0) as f:
  f.seek(lb);h=f.read(lb);row['gpt_signature']=h[:8]==b'EFI PART'
  if row['gpt_signature']:
   hs=struct.unpack_from('<I',h,12)[0];crc=struct.unpack_from('<I',h,16)[0];hb=bytearray(h[:hs]);hb[16:20]=b'\0'*4;row['header_crc_valid']=zlib.crc32(hb)==crc;entry_lba,count,es=struct.unpack_from('<QII',h,72);f.seek(entry_lba*lb);b=f.read(count*es);row.update(entry_lba=entry_lba,entry_count=count,entry_size=es,entries_crc_valid=zlib.crc32(b)==struct.unpack_from('<I',h,88)[0])
 out.append(row)
print(json.dumps(dict(report=dict(luns=out))))
