from pathlib import Path
import base64,gzip,hashlib,importlib.util,io,json,tarfile
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel248');spec=importlib.util.spec_from_file_location('host',R.parent/'kernel247/host.py');host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
code=r'''
from pathlib import Path
import base64,hashlib,io,json,struct,tarfile,zlib
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k247-runtime/boot-id-private.txt').read_bytes();data={};manifest={}
for name in ['sda','sdb','sdc','sdd','sde','sdf']:
 p=Path('/sys/class/block')/name;size=int((p/'size').read_text())*512;lb=int((p/'queue/logical_block_size').read_text());assert size>524288 and lb==4096
 with open('/dev/'+name,'rb',buffering=0) as f:
  f.seek(lb);h=f.read(lb);assert h[:8]==b'EFI PART';hs=struct.unpack_from('<I',h,12)[0];crc=struct.unpack_from('<I',h,16)[0];hb=bytearray(h[:hs]);hb[16:20]=b'\0'*4;assert zlib.crc32(hb)==crc;entry_lba,count,es=struct.unpack_from('<QII',h,72);assert entry_lba==2 and count in [32,64] and es==128
  f.seek(entry_lba*lb);entries=f.read(count*es);assert zlib.crc32(entries)==struct.unpack_from('<I',h,88)[0];first_usable,last_usable=struct.unpack_from('<QQ',h,40);first_bytes=first_usable*lb;last_bytes=size-(last_usable+1)*lb;assert 0<first_bytes<=1024*1024 and 0<last_bytes<=1024*1024
  f.seek(size-lb);back=f.read(lb);assert back[:8]==b'EFI PART';bh=bytearray(back[:struct.unpack_from('<I',back,12)[0]]);bh[16:20]=b'\0'*4;assert zlib.crc32(bh)==struct.unpack_from('<I',back,16)[0];blba,bcount,bes=struct.unpack_from('<QII',back,72);assert (bcount,bes)==(count,es);f.seek(blba*lb);assert f.read(count*es)==entries
  for end,offset,n in [('first',0,first_bytes),('last',size-last_bytes,last_bytes)]:
   f.seek(offset);b=f.read(n);assert len(b)==n;label=name+'-'+end+'.bin';data[label]=b;manifest[label]=dict(offset=offset,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),disk_bytes=size,logical_block_size=lb,primary_header_and_entries_crc_verified=True)
buffer=io.BytesIO()
with tarfile.open(fileobj=buffer,mode='w:gz') as archive:
 for name,b in data.items():
  info=tarfile.TarInfo(name);info.mode=0o600;info.size=len(b);archive.addfile(info,io.BytesIO(b))
blob=buffer.getvalue();assert len(blob)<128*1024
print(json.dumps(dict(archive_base64=base64.b64encode(blob).decode(),manifest=manifest,archive_sha256=hashlib.sha256(blob).hexdigest())))
'''
x=host.ssh('python3 -',input=code.encode(),timeout=20);v=json.loads(x.stdout);b=base64.b64decode(v.pop('archive_base64'));assert hashlib.sha256(b).hexdigest()==v['archive_sha256'];out=P/'linux-return-gpt-private.tar.gz';assert not out.exists();out.write_bytes(b);(P/'linux-return-gpt-manifest-private.json').write_text(json.dumps(v,indent=2)+'\n')
with tarfile.open(fileobj=io.BytesIO(b),mode='r:gz') as archive:
 assert len(archive.getmembers())==12
 for member in archive:
  data=archive.extractfile(member).read();assert hashlib.sha256(data).hexdigest()==v['manifest'][member.name]['sha256']
report=dict(stage=248,ufs_luns=6,gpt_head_and_tail_members=12,all_lengths_and_sha256_verified=True,phone_read_only=True,old_factory_backups_not_overwritten=True);(R/'gpt-backup-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
