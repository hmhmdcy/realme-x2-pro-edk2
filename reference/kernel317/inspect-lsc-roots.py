"""Locate factory LSC mode roots and their typed golden/table references."""
from pathlib import Path
import json,struct
import host
raw=(host.PRIVATE.parent/'kernel298/sunny-imx319-tuning-private.bin').read_bytes()
table,count=struct.unpack_from('<II',raw,0x98)
sections=[struct.unpack_from('<QQQ',raw,table+i*24) for i in range(count)]
_,start,length=sections[0];base,size=sections[1][1:]
entries={}
for pos in range(start,start+length,72):
 uid=struct.unpack_from('<Q',raw,pos)[0]
 name=raw[pos+8:pos+40].split(b'\0')[0].decode()
 version,incr=struct.unpack_from('<II',raw,pos+40)
 offset,nbytes=struct.unpack_from('<QQ',raw,pos+56)
 assert offset+nbytes<=size
 entries[uid]=dict(name=name,version=version,increment=incr,offset=offset,bytes=nbytes)
roots=[]
for uid,entry in entries.items():
 if entry['name'] not in ['lsc34_ife','lsc34_bps'] or not entry['version']:continue
 assert entry['bytes']%8==0
 words=list(struct.unpack_from('<'+'Q'*(entry['bytes']//8),raw,base+entry['offset']))
 refs=[dict(word=i,uid=v,name=entries[v]['name'],bytes=entries[v]['bytes']) for i,v in enumerate(words) if v in entries and v>1000]
 roots.append(dict(uid=uid,**entry,words=words,references=refs))
(host.PRIVATE/'lsc-root-index-private.json').write_text(json.dumps(dict(base=base,entries=entries,roots=roots),indent=2)+'\n')
print(json.dumps(dict(root_count=len(roots),names={name:sum(r['name']==name for r in roots) for name in ['lsc34_ife','lsc34_bps']},first_ife=next(r for r in roots if r['name']=='lsc34_ife')),indent=2))
