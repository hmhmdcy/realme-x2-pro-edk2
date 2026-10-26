"""Inspect only the typed EEPROM prefix; do not trust old full-layout XML."""
from pathlib import Path
import json,struct
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;reports=[]
for name in ['sunny_s5kgw1','qtech_s5kgw1','sunny_imx471','qtech_s5k3m5sx']:
 path=P.parent/'kernel115/vendor-camera-bins'/('com.qti.sensormodule.'+name+'.bin');raw=path.read_bytes()
 table,count=struct.unpack_from('<II',raw,0x98);sections=[struct.unpack_from('<QQQ',raw,table+i*24) for i in range(count)]
 _,start,length=sections[0];base,size=sections[1][1:];entries={}
 for pos in range(start,start+length,72):
  uid=struct.unpack_from('<Q',raw,pos)[0];tag=raw[pos+8:pos+40].split(b'\0')[0].decode();offset,n=struct.unpack_from('<QQ',raw,pos+56)
  assert offset+n<=size;entries[uid]=(tag,offset,n)
 def data(uid,tag):
  actual,offset,n=entries[uid];assert actual==tag;return raw[base+offset:base+offset+n]
 def scalar(uid,tag):
  b=data(uid,tag);assert len(b)==8;return struct.unpack('<Q',b)[0]
 uid=next(u for u,e in entries.items() if e[0]=='EEPROMDriverData');blob=data(uid,'EEPROMDriverData');assert len(blob)%8==0
 words=struct.unpack('<'+'Q'*(len(blob)//8),blob);assert words[:3]==(1,0,0)
 epname=data(words[4],'EEPROMName').rstrip(b'\0').decode();count=words[13];b=data(words[14],'regSetting');assert len(b)==count*80
 operations=[]
 for offset in range(0,len(b),80):
  record=struct.unpack_from('<10Q',b,offset);assert record[0]==record[3]==record[8]==1
  operations.append(dict(slave_address8=scalar(record[1],'slaveAddr'),register_address=record[2],register_data=scalar(record[4],'registerData'),
   register_address_bytes=record[5],register_data_bytes=record[6],operation_enum=record[7],delay_us=scalar(record[9],'delayUs')))
 lights=[dict(uid=u,bytes=e[2],root_reference_words=[i for i,w in enumerate(words) if w==u]) for u,e in entries.items() if e[0]=='lightInfo']
 reports.append(dict(module=name,eeprom_name=epname,eeprom_root_words=len(words),declared_slave_address8=words[5],memory_map=operations,typed_light_arrays=lights))
report=dict(stage=324,modules=reports,prefix_only=True,full_layout_or_checksum_not_verified=True,no_phone_operations=True,passed=True)
(HERE/'module-calibration-prefix-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
