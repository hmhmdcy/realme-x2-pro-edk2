"""Reconstruct full OTA new.dat.br payloads as private sparse host files."""
from pathlib import Path
import brotli,hashlib,json,struct,sys,zipfile
R=Path(__file__).resolve().parent;O=Path('/mnt/e/edk2-samurai-out/kernel242/android-rom')
Z=Path('/mnt/c/Users/cy122/Downloads/crDroidAndroid-16.0-20251217-samurai-v12.4.zip')
sizes=dict(system=4487905280,vendor=1711276032,odm=268435456)
reports={}
with zipfile.ZipFile(Z) as z:
 for part in sys.argv[1:]:
  assert part in sizes
  target=O/(part+'.img');assert not target.exists(), 'Do not overwrite a prior reconstructed image'
  lines=z.read(part+'.transfer.list').decode().splitlines();assert lines[0]=='4' and lines[2:4]==['0','0']
  ranges=[];affected=0
  for line in lines[4:]:
   op,blockset=line.split();assert op in ['new','zero','erase']
   nums=[int(x) for x in blockset.split(',')];assert nums[0]==len(nums)-1 and nums[0]%2==0
   for i in range(1,len(nums),2):
    a,b=nums[i:i+2];assert 0<=a<b<=sizes[part]//4096
    if op=='new':ranges.append((a*4096,b*4096))
    if op in ['new','zero']:affected+=b-a
  expected=sum(b-a for a,b in ranges);assert affected==int(lines[1])
  dec=brotli.Decompressor();index=0;written=0;position=ranges[0][0]
  with target.open('xb') as dst,z.open(part+'.new.dat.br') as src:
   dst.truncate(sizes[part]);dst.seek(position)
   while compressed:=src.read(64*1024):
    plain=memoryview(dec.process(compressed));offset=0
    while offset<len(plain):
     assert index<len(ranges),'Too much decompressed data'
     n=min(len(plain)-offset,ranges[index][1]-position)
     dst.write(plain[offset:offset+n]);position+=n;written+=n;offset+=n
     if position==ranges[index][1]:
      index+=1
      if index<len(ranges):position=ranges[index][0];dst.seek(position)
   assert dec.is_finished() and written==expected and index==len(ranges)
  with target.open('rb') as f:f.seek(1080);assert f.read(2)==b'\x53\xef'
  report=dict(partition=part,image_bytes=target.stat().st_size,new_data_bytes=written,ranges=len(ranges),brotli_finished=True,zip_member_crc_checked=True,ext4_magic=True,no_phone_changes=True)
  (O/(part+'-unpack-validation.json')).write_text(json.dumps(report,indent=2)+'\n');reports[part]=report
  print(json.dumps(report),flush=True)
(R/'rom-partition-unpack-validation.json').write_text(json.dumps(reports,indent=2)+'\n')
