from pathlib import Path
import collections,json,struct
P=Path('/mnt/e/edk2-samurai-out/kernel298');raw=(P/'sunny-imx319-tuning-private.bin').read_bytes()
table,count=struct.unpack_from('<II',raw,0x98);sections=[struct.unpack_from('<QQQ',raw,table+i*24) for i in range(count)]
_,so,ss=sections[0];_,base,size=sections[1];assert ss%72==0
rows=[]
for pos in range(so,so+ss,72):
 uid=struct.unpack_from('<Q',raw,pos)[0];name=raw[pos+8:pos+40].split(b'\0')[0].decode();offset,length=struct.unpack_from('<QQ',raw,pos+56)
 assert offset<=size and length<=size-offset
 rows.append(dict(uid=uid,name=name,offset=offset,size=length,record_offset=pos))
(P/'imx319-tuning-symbols-private.json').write_text(json.dumps(dict(base=base,data_size=size,symbols=rows),indent=2)+'\n')
names=collections.Counter(r['name'] for r in rows)
matches={n:c for n,c in names.items() if any(k in n.lower() for k in ['bls','black','awb','color','cc12'])}
print(json.dumps(dict(symbols=len(rows),unique_names=len(names),matching_names=matches),indent=2))
