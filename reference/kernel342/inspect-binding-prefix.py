"""Inventory existing typed probe/identity fields, without exposing unit bytes."""
from pathlib import Path
import json,struct
import host
HERE=Path(__file__).resolve().parent;sources=json.loads((host.PRIVATE.parent/'kernel326/descriptor-sources-private.json').read_text());rows={}
for name in ['qtech_s5kgw1','sunny_s5kgw1']:
 raw=Path(sources[name]['local_path']).read_bytes();table,count=struct.unpack_from('<II',raw,0x98);sections=[struct.unpack_from('<QQQ',raw,table+i*24) for i in range(count)];_,start,length=sections[0];base,size=sections[1][1:];entries=[]
 for pos in range(start,start+length,72):
  uid=struct.unpack_from('<Q',raw,pos)[0];tag=raw[pos+8:pos+40].split(b'\0')[0].decode();offset,n=struct.unpack_from('<QQ',raw,pos+56)
  if any(word.lower() in tag.lower() for word in ['module','vendor','manufacturer','slave','sensorid','probe','eeprom','custom','match']):
   assert offset+n<=size;item=dict(uid=uid,tag=tag,bytes=n)
   if n<=128 and n%8==0:item['words']=list(struct.unpack_from('<'+'Q'*(n//8),raw,base+offset))
   entries.append(item)
 rows[name]=entries
(host.PRIVATE/'typed-probe-prefix-private.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps({name:dict(fields=len(entries),tags=sorted({r['tag'] for r in entries})) for name,entries in rows.items()}))
