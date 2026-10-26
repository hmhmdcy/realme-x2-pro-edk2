"""Compare declared IMX319 vendor layouts against the retained EEPROM sample."""
from pathlib import Path
import json,struct
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
sample=(P.parent/'kernel299/imx319-eeprom-read1-private.bin').read_bytes()
reports=[]
for vendor in ['sunny','qtech']:
 raw=(P.parent/('kernel115/vendor-camera-bins/com.qti.sensormodule.'+vendor+'_imx319.bin')).read_bytes()
 table,count=struct.unpack_from('<II',raw,0x98)
 sections=[struct.unpack_from('<QQQ',raw,table+i*24) for i in range(count)]
 _,start,length=sections[0];base,size=sections[1][1:];entries={}
 for pos in range(start,start+length,72):
  uid=struct.unpack_from('<Q',raw,pos)[0]
  name=raw[pos+8:pos+40].split(b'\0')[0].decode()
  offset,nbytes=struct.unpack_from('<QQ',raw,pos+56)
  assert offset+nbytes<=size
  entries[uid]=dict(name=name,offset=offset,bytes=nbytes)
 def words(uid):
  e=entries[uid];assert e['bytes']%8==0
  return struct.unpack_from('<'+'Q'*(e['bytes']//8),raw,base+e['offset'])
 root=words(next(uid for uid,e in entries.items() if e['name']=='EEPROMDriverData'))
 row=dict(vendor_descriptor=vendor,root_words=len(root),candidates=[])
 for uid,e in entries.items():
  if e['name']!='lightInfo':continue
  refs=[i for i,v in enumerate(root) if v==uid]
  if len(refs)!=1:continue
  pos=refs[0];n=root[pos-1]
  if not n:continue
  row['candidates'].append(dict(uid=uid,records=n,words_per_record=e['bytes']//8//n,root_reference=pos))
  if e['bytes']!=n*17*8:continue
  mesh=root[pos+1];increments=root[pos+2:pos+6];light=words(uid)[:17]
  values=[];addresses=[]
  for c in range(4):
   msb,msbmask,lsb,lsbmask=light[1+c*4:5+c*4];inc=increments[c]
   def part(offset,mask):
    assert 0<mask<=255
    return (sample[offset]&mask)//(mask&-mask)
   values.append([(part(msb+i*inc,msbmask)<<8)|part(lsb+i*inc,lsbmask) for i in range(mesh)])
   addresses += [msb,lsb,msb+(mesh-1)*inc,lsb+(mesh-1)*inc]
  row['lsc_candidate']=dict(points=mesh,channel_steps=list(increments),declared_address_bounds=[min(addresses),max(addresses)],
   zeros=sum(v==0 for channel in values for v in channel),unique_light_address_maps=len({tuple(words(uid)[i*17+1:(i+1)*17]) for i in range(n)}))
 reports.append(row)
(HERE/'module-layout-comparison.json').write_text(json.dumps(dict(stage=317,descriptors=reports,physical_vendor_not_determined=True,individual_values_not_applied=True),indent=2)+'\n')
print(json.dumps(reports,indent=2))
