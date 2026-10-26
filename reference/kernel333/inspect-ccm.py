from pathlib import Path
import hashlib,json,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
repo=Path('/home/cy122/x2pro-linux/refs/CamxChi-k117');commit=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
assert commit=='9f17f1b568626b393e785b369c5dc94543774d7a'
names=['chi-cdk/api/chromatix/XSD/isp/cc_1_2_0.xsd','camx/src/hwl/iqinterpolation/ifecc12interpolation.cpp',
 'camx/src/hwl/iqsetting/ifecc12setting.cpp','camx/src/hwl/iqsetting/ifecc12setting.h',
 'camx/src/hwl/isphwsetting/titan17x/camxifecc12titan17x.cpp','camx/src/hwl/isphwsetting/titan17x/camxifecc12titan17x.h']
sources=[];(P/'sources').mkdir(exist_ok=True)
for name in names:
 raw=subprocess.check_output(['git','-C',str(repo),'show',commit+':'+name]);(P/'sources'/Path(name).name).write_bytes(raw)
 sources.append(dict(repository='https://github.com/bjzhou/CamxChi',commit=commit,path=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
(HERE/'primary-sources.json').write_text(json.dumps(dict(stage=333,sources=sources,source_access='retained pinned Git repository'),indent=2)+'\n')
rows=[]
for name,stage,filename in [('qtech_s5kgw1',324,'qtech_s5kgw1-tuning-private.bin'),('sunny_s5kgw1',324,'sunny_s5kgw1-tuning-private.bin'),
 ('sunny_imx471',324,'sunny_imx471-tuning-private.bin'),('qtech_s5k3m5sx',306,'qtech-s5k3m5sx-tuning-private.bin'),('sunny_imx319',298,'sunny-imx319-tuning-private.bin')]:
 raw=(P.parent/('kernel'+str(stage))/filename).read_bytes();table,count=struct.unpack_from('<II',raw,0x98)
 sections=[struct.unpack_from('<QQQ',raw,table+i*24) for i in range(count)];start,length=sections[0][1:];base,size=sections[1][1:];entries={}
 for pos in range(start,start+length,72):
  uid=struct.unpack_from('<Q',raw,pos)[0];tag=raw[pos+8:pos+40].split(b'\0')[0].decode();version,incr=struct.unpack_from('<II',raw,pos+40);offset,nbytes=struct.unpack_from('<QQ',raw,pos+56)
  entries[str(uid)]=dict(name=tag,version=version,increment=incr,offset=offset,bytes=nbytes)
 roots=[]
 for uid,e in entries.items():
  if not e['version'] or e['name']!='cc12_ife':continue
  data=raw[base+e['offset']:base+e['offset']+e['bytes']];words=struct.unpack('<'+'Q'*(len(data)//8),data)
  refs=[dict(word=i,uid=v,tag=entries[str(v)]['name'],bytes=entries[str(v)]['bytes']) for i,v in enumerate(words) if str(v) in entries]
  roots.append(dict(uid=int(uid),bytes=len(data),references=refs,words=list(words)))
 (P/(name+'-index-private.json')).write_text(json.dumps(dict(name=name,source_stage=stage,filename=filename,base=base,sections=sections,entries=entries,roots=roots),indent=2)+'\n')
 rows.append(dict(name=name,roots=roots))
print(json.dumps([dict(name=r['name'],roots=[p['uid'] for p in r['roots']]) for r in rows],indent=2))
