from pathlib import Path
import json,struct
import host
P=host.PRIVATE;rows=[];sources=json.loads((P.parent/'kernel326/descriptor-sources-private.json').read_text())
for name in ['qtech_s5kgw1','sunny_s5kgw1']:
 raw=Path(sources[name]['local_path']).read_bytes();table,count=struct.unpack_from('<II',raw,0x98);sections=[struct.unpack_from('<QQQ',raw,table+i*24) for i in range(count)];start,length=sections[0][1:];base=sections[1][1];entries={}
 for pos in range(start,start+length,72):
  uid=struct.unpack_from('<Q',raw,pos)[0];tag=raw[pos+8:pos+40].split(b'\0')[0].decode();offset,n=struct.unpack_from('<QQ',raw,pos+56);entries[uid]=(tag,offset,n)
 def data(uid):
  tag,offset,n=entries[uid];return raw[base+offset:base+offset+n]
 names={}
 for uid,(tag,off,n) in entries.items():
  if tag not in ['moduleName','sensorName','eepromName','actuatorName','Name']:continue
  blob=data(uid)
  if blob and 32<=blob[0]<127 and all(c==0 or 32<=c<127 for c in blob):names[tag]=blob.rstrip(b'\0').decode();continue
  if len(blob)!=16:continue
  length,ref=struct.unpack('<QQ',blob)
  if ref in entries:
   payload=data(ref)
   if len(payload)==(length+7)//8*8:names[tag]=payload[:length].rstrip(b'\0').decode()
 rows.append(dict(descriptor=name,names=names))
(P/'module-names-private.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows))
