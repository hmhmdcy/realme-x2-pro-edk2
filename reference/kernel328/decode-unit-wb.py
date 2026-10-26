"""Format all retained unit WB with current descriptors and exact HAL arithmetic."""
from pathlib import Path
import json, math, struct, xml.etree.ElementTree as ET
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
hal=(P.parent/'kernel316/hal-source/camera.qcom.so').read_bytes()
# These are real instructions in the inlined stock FormatWBData branch.
instructions={0x4fd14c:0xbd412b84,0x4fd150:0x1e202088,0x4fd158:0x52a7f018,
 0x4fd5d8:0x540060a0,0x4fe2e0:0x35fff939,0x4fe220:0x1e3d1901,
 0x4fe228:0x2e27fe11,0x4fe22c:0x1e3e1822,0x4fe230:0x2e32fe33,
 0x4fd814:0xbd71c366,0x4fd818:0x1e261907,0x4fd820:0x1e261cf0}
assert all(struct.unpack_from('<I',hal,at)[0]==value for at,value in instructions.items())
layouts=json.loads((P.parent/'kernel326/descriptor-layouts-private.json').read_text())
source=P.parent/'kernel115/vendor-camera-bins/com.qti.sensormodule.sunny_imx319.bin'
raw=source.read_bytes();table,count=struct.unpack_from('<II',raw,0x98)
sections=[struct.unpack_from('<QQQ',raw,table+i*24) for i in range(count)]
start,length=sections[0][1:];base,size=sections[1][1:];entries={}
for pos in range(start,start+length,72):
 uid=struct.unpack_from('<Q',raw,pos)[0];tag=raw[pos+8:pos+40].split(b'\0')[0].decode();offset,n=struct.unpack_from('<QQ',raw,pos+56)
 assert offset+n<=size;entries[uid]=(tag,offset,n)
root_entry=next(e for e in entries.values() if e[0]=='EEPROMDriverData')
root=struct.unpack_from('<'+'Q'*(root_entry[2]//8),raw,base+root_entry[1])
uid=next(u for u,e in entries.items() if e[0]=='lightInfo' and e[2]==600)
at=root.index(uid);offset=entries[uid][1]
rows=[list(struct.unpack_from('<15Q',raw,base+offset+i*120)) for i in range(5)]
layouts['sunny_imx319']=dict(lights=dict(wb=dict(prefix=list(root[at-4:at+7]),rows=rows)))
schema=P.parent/'kernel317/sources/camxeepromdriver-2020.xsd'
ns={'x':'http://www.w3.org/2001/XMLSchema'}
names=[e.attrib['value'] for e in ET.parse(schema).findall("x:simpleType[@name='EEPROMIlluminantType']/x:restriction/x:enumeration",ns)]
assert names==['D65','TL84','A','D50','H','MAX']
f32=lambda value:struct.unpack('<f',struct.pack('<f',value))[0]
decoded={};reports=[]
for name,item in layouts.items():
 model='s5kgw1' if name.endswith('s5kgw1') else 'imx471' if name.endswith('imx471') else 'imx319' if name.endswith('imx319') else 's5k3m5'
 source=P.parent/'kernel299/imx319-eeprom-read1-private.bin' if model=='imx319' else P.parent/'kernel326/reads-r2'/(model+'-read1-private.bin')
 data=source.read_bytes();wb=item['lights']['wb'];prefix=wb['prefix']
 assert prefix[:4]==[1,1,0,5] and prefix[5:9]==[0,0,0,0] and prefix[10] in [0,1],(name,prefix)
 q=struct.unpack('<f',struct.pack('<I',prefix[9]))[0];q=1. if q==0 else q
 assert math.isfinite(q) and q>0
 def integer(address,mask):
  assert mask in [0,65535]
  return int.from_bytes(data[address:address+2],'little') if mask else 0
 lights=[]
 for row in wb['rows']:
  r,gr,b,gb=[integer(row[i],row[i+1]) for i in [1,3,5,7]]
  assert gb>0
  ratios=[f32(f32(f32(v)/f32(gb))/q) for v in [r,b,gr]]
  assert all(math.isfinite(v) and v>0 for v in ratios)
  lights.append(dict(illuminant=row[0],illuminant_name=names[row[0]],channels=[r,gr,gb,b],
   q_value=q,mirror=0,gr_gb_inverted=False,stock_float32_r_over_gb=ratios[0],stock_float32_b_over_gb=ratios[1],stock_float32_gr_over_gb=ratios[2]))
 decoded[name]=lights
 reports.append(dict(module=name,model=model,illuminants=[v['illuminant_name'] for v in lights],
  positive_denominators=True,q_value=q,mirror_mask_zero=True,invert_gr_gb_flag=bool(prefix[10]),conditional_green_inversion_inactive=True,
  datatype='INDIVIDUAL',endianness='LITTLE',channel_ratios_reference='Gb',
  current_326_decoded_channel_values_retained=True if model!='imx319' else None))
 if model!='imx319':
  old=json.loads((P.parent/'kernel326/decoded-unit-private.json').read_text())[name]['wb']
  assert all(a['channels']==b['channels'] and a['illuminant']==b['illuminant'] for a,b in zip(old,lights))
(P/'formatted-unit-wb-private.json').write_text(json.dumps(decoded,indent=2)+'\n')
report=dict(stage=328,modules=reports,exact_hal_instruction_locations={hex(k):hex(v) for k,v in instructions.items()},
 stock_q_value_zero_defaults_to_one=True,stock_gr_over_gb_inverts_only_when_mirror_nonzero=True,
 source_schema_commit='36fc163a534963a5b3af52186af5efcc63401ad2',
 no_new_eeprom_reads=True,unit_values_not_repaired=True,unit_white_balance_applied=False,
 checksum_verified=False,phone_changed=False,passed=True)
(HERE/'unit-wb-format-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
