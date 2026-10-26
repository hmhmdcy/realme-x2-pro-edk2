"""Derive read-only transactions from current factory typed descriptors."""
from pathlib import Path
import json,struct
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
sources=json.loads((P/'descriptor-sources-private.json').read_text());plans=[];layouts={}
for name,source in sources.items():
 raw=Path(source['local_path']).read_bytes();table,count=struct.unpack_from('<II',raw,0x98);sections=[struct.unpack_from('<QQQ',raw,table+i*24) for i in range(count)]
 _,start,length=sections[0];base,size=sections[1][1:];entries={}
 for pos in range(start,start+length,72):
  uid=struct.unpack_from('<Q',raw,pos)[0];tag=raw[pos+8:pos+40].split(b'\0')[0].decode();offset,n=struct.unpack_from('<QQ',raw,pos+56);assert offset+n<=size;entries[uid]=(tag,offset,n)
 def data(uid,tag=None):
  actual,offset,n=entries[uid];assert tag is None or actual==tag;return raw[base+offset:base+offset+n]
 def words(uid,tag=None):
  b=data(uid,tag);assert len(b)%8==0;return struct.unpack('<'+'Q'*(len(b)//8),b)
 def scalar(uid,tag):
  b=data(uid,tag);assert len(b)==8;return struct.unpack('<Q',b)[0]
 uid=next(u for u,e in entries.items() if e[0]=='EEPROMDriverData');root=words(uid);assert root[:3]==(1,0,0)
 epname=data(root[4],'EEPROMName').rstrip(b'\0').decode();count=root[13];b=data(root[14],'regSetting');assert len(b)==count*80
 operations=[]
 for offset in range(0,len(b),80):
  record=struct.unpack_from('<10Q',b,offset);assert record[0]==record[3]==record[8]==1
  operations.append(dict(address8=scalar(record[1],'slaveAddr'),start=record[2],bytes=scalar(record[4],'registerData'),address_bytes=record[5],data_bytes=record[6],operation_enum=record[7],delay_us=scalar(record[9],'delayUs')))
 assert len(operations)==1;op=operations[0];assert op['address8']==root[5] and op['operation_enum']==3 and op['address_bytes']==2 and op['data_bytes']==1 and op['start']==0
 lights={}
 for u,e in entries.items():
  if e[0]!='lightInfo':continue
  positions=[i for i,v in enumerate(root) if v==u]
  if len(positions)!=1:continue
  at=positions[0];n=root[at-1]
  if e[2]==n*15*8:lights['wb']=dict(root_word=at-4,prefix=list(root[at-4:at+7]),rows=[list(words(u)[i*15:(i+1)*15]) for i in range(n)])
  if e[2]==n*17*8:lights['lsc']=dict(root_word=at-3,prefix=list(root[at-3:at+6]),rows=[list(words(u)[i*17:(i+1)*17]) for i in range(n)])
 layouts[name]=dict(eeprom_name=epname,root=list(root),lights=lights,source_sha256=source['sha256'])
 model='s5kgw1' if name.endswith('s5kgw1') else 'imx471' if name.endswith('imx471') else 's5k3m5'
 plans.append(dict(module=name,model=model,eeprom_name=epname,address7=op['address8']>>1,read_bytes=op['bytes'],address_bytes=2,data_bytes=1,start=0,operation='READ',source_sha256=source['sha256'],root_words=len(root),light_layouts={k:dict(elements=len(v['rows']),root_word=v['root_word']) for k,v in lights.items()}))
# Both main descriptors point to the same physical read map; read it once.
deduplicated=[]
for p in plans:
 prior=next((r for r in deduplicated if r['model']==p['model']),None)
 if prior:
  assert all(prior[k]==p[k] for k in ['address7','read_bytes','address_bytes','data_bytes','start']);prior['alternate_descriptor']=p['module']
 else:deduplicated.append(p.copy())
(P/'descriptor-layouts-private.json').write_text(json.dumps(layouts,indent=2)+'\n')
report=dict(stage=326,plans=deduplicated,current_factory_descriptors_verified=True,prefix_read_operations_only=True,no_calibration_applied=True,passed=True)
(HERE/'read-plan-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
