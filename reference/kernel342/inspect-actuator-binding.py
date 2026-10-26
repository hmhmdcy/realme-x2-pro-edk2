from pathlib import Path
import json,struct
import host
P=host.PRIVATE;sources=json.loads((P.parent/'kernel326/descriptor-sources-private.json').read_text());rows=[]
for name in ['qtech_s5kgw1','sunny_s5kgw1']:
 raw=Path(sources[name]['local_path']).read_bytes();table,count=struct.unpack_from('<II',raw,0x98);sections=[struct.unpack_from('<QQQ',raw,table+i*24) for i in range(count)];start,length=sections[0][1:];base=sections[1][1];entries={}
 for pos in range(start,start+length,72):
  uid=struct.unpack_from('<Q',raw,pos)[0];tag=raw[pos+8:pos+40].split(b'\0')[0].decode();offset,n=struct.unpack_from('<QQ',raw,pos+56);entries[uid]=(tag,offset,n)
 def data(uid):
  tag,offset,n=entries[uid];return raw[base+offset:base+offset+n]
 selected=[]
 for uid,(tag,off,n) in entries.items():
  if tag=='ActuatorDriverData':
   root=struct.unpack('<'+'Q'*(n//8),data(uid));selected.append(dict(uid=uid,tag=tag,words=list(root),references=[dict(word=i,uid=value,tag=entries[value][0],bytes=entries[value][2]) for i,value in enumerate(root) if value in entries and value>3]))
 rows.append(dict(descriptor=name,actuator_roots=selected))
(P/'actuator-prefix-private.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows))
