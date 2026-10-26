"""Bounded offline decoder for same-handset Parameter Parser 1.3.2 BINs.

Decodes only the verified fixed sensor prefix, external strings and power triples.
Does not decode calibration/EEPROM, generate sensor register writes or access hardware.
"""
from pathlib import Path
import struct, json, hashlib, xml.etree.ElementTree as ET
BIN_ROOT=Path('/mnt/e/edk2-samurai-out/kernel115/vendor-camera-bins')
SOURCE=Path('/mnt/e/edk2-samurai-out/kernel117/CamxChi/chi-cdk/api/sensor')
OUT=Path('/mnt/e/edk2-samurai-out/kernel192')
NS={'x':'http://www.w3.org/2001/XMLSchema'}
schema=ET.parse(SOURCE/'camxsensorcommon.xsd')
enum_nodes=schema.findall(".//x:simpleType[@name='PowerConfigurationType']//x:enumeration",NS)
enums=[e.attrib['value'] for e in enum_nodes]
assert enums
def decode(p):
 b=p.read_bytes()
 assert b.startswith(b'QTI Chromatix Header\0')
 assert struct.unpack_from('<I',b,28)[0]==len(b)
 assert b'Parameter Parser V1.3.2 ' in b[:0x98]
 section_offset,count=struct.unpack_from('<II',b,0x98)
 assert count==3 and section_offset==0xa0
 sections=[struct.unpack_from('<QQQ',b,section_offset+i*24) for i in range(count)]
 assert [s[0] for s in sections]==[0,1,2]
 for _,off,sz in sections:assert off+sz<=len(b)
 _,symoff,symsize=sections[0];_,dataoff,datasize=sections[1]
 assert symsize%72==0
 entries={}
 for off in range(symoff,symoff+symsize,72):
  ident=struct.unpack_from('<Q',b,off)[0]
  name=b[off+8:off+40].split(b'\0')[0].decode('ascii')
  root=struct.unpack_from('<I',b,off+40)[0]
  data,sz=struct.unpack_from('<QQ',b,off+56)
  assert data+sz<=datasize and ident not in entries
  entries[ident]=dict(id=ident,name=name,root=root,offset=data,size=sz)
 def payload(ident,name):
  e=entries[ident];assert e['name']==name
  return b[dataoff+e['offset']:dataoff+e['offset']+e['size']]
 roots=[e for e in entries.values() if e['root']==1 and e['name']=='sensorDriverData'];assert len(roots)==1
 root=payload(roots[0]['id'],'sensorDriverData');assert len(root)>=0x80
 words=struct.unpack_from('<16Q',root)
 major,minor,incr,nlen,nref,slave,addrtype,datatype,idreg,sensorid,mask,frequency,upn,upr,downn,downr=words
 assert major==1 and slave<=0xfe and slave%2==0 and addrtype in [1,2,3] and datatype in [1,2,3]
 assert 1<=nlen<=64 and 1<=upn<=32 and 1<=downn<=32
 name=payload(nref,'sensorName');assert len(name)==(nlen+7)//8*8
 assert name[nlen:]==bytes(len(name)-nlen)
 name=name[:nlen].rstrip(b'\0').decode('ascii')
 def power(n,ref):
  data=payload(ref,'powerSetting');assert len(data)==n*24
  result=[]
  for off in range(0,len(data),24):
   typ,value,delay=struct.unpack_from('<QQQ',data,off)
   assert typ<len(enums) and delay<=1000 and value<=100000000
   result.append(dict(type=enums[typ],enum_value=typ,value=value,delay_ms=delay))
  return result
 module_roots=[e for e in entries.values() if e['root']==1 and e['name']=='cameraModuleData'];assert len(module_roots)==1
 module_root=payload(module_roots[0]['id'],'cameraModuleData');assert len(module_root)==40
 module_words=struct.unpack('<5Q',module_root);assert module_words[:4]==(1,0,0,1)
 mod=payload(module_words[4],'moduleConfiguration');assert len(mod)%8==0 and len(mod)>=72
 m=struct.unpack('<'+'Q'*(len(mod)//8),mod)
 # Optional string: presence/length/reference. Optional primitive: count/reference.
 slot=m[0];assert slot<=4
 assert m[3]==nlen and payload(m[4],'sensorName').rstrip(b'\0').decode()==name
 assert m[5]==0 and m[7]==0, 'Unimplemented module override must not be ignored'
 assert payload(m[6],'sensorSlaveAddress')==b'' and payload(m[8],'sensorI2CFrequencyMode')==b''
 module=dict(camera_slot=slot,slave_address_override_present=False,i2c_frequency_override_present=False)
 return dict(file=p.name,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),version=[major,minor,incr],sensor=name,module=module,
  slave_address_8bit=slave,i2c_address_7bit=slave>>1,reg_address_type=addrtype,reg_data_type=datatype,
  id_register=idreg,id_value=sensorid,id_mask=mask,i2c_frequency_enum=frequency,power_up=power(upn,upr),power_down=power(downn,downr))
records=[decode(p) for p in sorted(BIN_ROOT.glob('com.qti.sensormodule.*.bin'))]
assert len(records)==6
report=dict(stage=192,scope='offline same-handset sensor prefix and power triples only',power_enum_source_sha256=hashlib.sha256((SOURCE/'camxsensorcommon.xsd').read_bytes()).hexdigest(),sensors=records,physical_camera_accepted=False)
(OUT/'camera-prefix-decoded-private.json').write_text(json.dumps(report,indent=2)+'\n')
for r in records:
 print(json.dumps(dict(file=r['file'],slot=r['module']['camera_slot'],address=hex(r['i2c_address_7bit']),id_register=hex(r['id_register']),id_value=hex(r['id_value']),power_up_steps=len(r['power_up']),power_down_steps=len(r['power_down']))))
