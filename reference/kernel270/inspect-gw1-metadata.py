"""Bounded, read-only decoding of this handset's two GW1 module descriptions."""
from pathlib import Path
import hashlib,json,math,struct,xml.etree.ElementTree as ET
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel270')
schema=ET.parse('/home/cy122/x2pro-linux/parser-k235-imx319-init-qtech/api/sensor/camxsensorcommon.xsd')
ns={'x':'http://www.w3.org/2001/XMLSchema'}
operations=[n.attrib['value'] for n in schema.findall("./x:simpleType[@name='OperationType']/x:restriction/x:enumeration",ns)]
assert operations==['WRITE','WRITE_BURST','WRITE_SEQUENTIAL','READ','POLL','MAX']
reports=[]
for module in ['qtech','sunny']:
 path=Path('/mnt/e/edk2-samurai-out/kernel115/vendor-camera-bins')/('com.qti.sensormodule.'+module+'_s5kgw1.bin')
 data=path.read_bytes();assert data.startswith(b'QTI Chromatix Header\0') and struct.unpack_from('<I',data,28)[0]==len(data)
 table,count=struct.unpack_from('<II',data,0x98);assert count==3 and table+count*24<=len(data)
 sections=[struct.unpack_from('<QQQ',data,table+i*24) for i in range(count)]
 for _,start,size in sections:assert start<=len(data) and size<=len(data)-start
 _,symbols,symbolsize=sections[0];_,base,size=sections[1];assert symbolsize%72==0
 entries={}
 for offset in range(symbols,symbols+symbolsize,72):
  ident=struct.unpack_from('<Q',data,offset)[0];name=data[offset+8:offset+40].split(b'\0')[0].decode('ascii')
  relative,length=struct.unpack_from('<QQ',data,offset+56)
  assert ident not in entries and relative<=size and length<=size-relative
  entries[ident]=dict(name=name,relative=relative,size=length)
 def payload(ident,name):
  row=entries[ident];assert row['name']==name
  return data[base+row['relative']:base+row['relative']+row['size']]
 def unique(name):
  found=[ident for ident,row in entries.items() if row['name']==name];assert len(found)==1,(name,len(found));return found[0]
 def qwords(ident,name):
  b=payload(ident,name);assert len(b)%8==0;return struct.unpack('<'+'Q'*(len(b)//8),b)
 def uints(ident,name,n):
  b=payload(ident,name);needed=n*4
  assert 0<n<=100000 and len(b)==((needed+7)//8)*8 and not any(b[needed:])
  return struct.unpack_from('<'+'I'*n,b)
 def regs(ident,n):
  b=payload(ident,'regSetting');assert len(b)==n*80 and 0<n<=100000
  result=[]
  for offset in range(0,len(b),80):
   f=struct.unpack_from('<10Q',b,offset)
   if not (f[0]==0 and f[5]==2 and f[6] in [1,2,4] and f[7]<5 and f[2]<=65535):
    failure=dict(module=module,reg_setting_uid=ident,record_index=offset//80,fields=list(f),
     reason='Record differs from previously verified WRITE layout; decode schema before supporting it',no_phone_operation=True)
    (R/'gw1-unsupported-record-validation.json').write_text(json.dumps(failure,indent=2)+'\n')
    raise ValueError(json.dumps(failure))
   values=uints(f[4],'registerData',f[3]);delays=uints(f[9],'delayUs',f[8])
   if not (len(values)==f[3] and len(delays)==f[8] and len(values)>0):
    failure=dict(module=module,reg_setting_uid=ident,record_index=offset//80,fields=list(f),
     value_count=len(values),delay_count=len(delays),reason='Array extent mismatch; no hardware use',no_phone_operation=True)
    (R/'gw1-unsupported-array-validation.json').write_text(json.dumps(failure,indent=2)+'\n')
    raise ValueError(json.dumps(failure))
   assert all(0<=v<(1<<(8*f[6])) for v in values) and all(0<=v<=1000000 for v in delays)
   result.append(dict(address=f[2],address_bytes=f[5],value_bytes=f[6],operation=operations[f[7]],values=list(values),delays_us=list(delays)))
  return result
 ri=qwords(unique('resolutionInfo'),'resolutionInfo');assert len(ri)==4 and ri[0]==1 and 0<ri[2]<=64
 modes_data=payload(ri[3],'resolutionData');assert len(modes_data)==ri[2]*256
 modes=[];registers=[]
 for i in range(ri[2]):
  f=struct.unpack_from('<32Q',modes_data,i*256);streamdata=payload(f[2],'streamConfiguration');assert len(streamdata)==f[1]*64
  streams=[]
  for j in range(f[1]):
   s=struct.unpack_from('<8Q',streamdata,j*64);streams.append(dict(vc=s[0],data_type=s[1],width=s[4],height=s[5],bits=s[6]))
  decoded=regs(f[19],f[18]);registers.append(decoded)
  fps=struct.unpack('<d',struct.pack('<Q',f[10]))[0];assert math.isfinite(fps) and 0<fps<=1000
  modes.append(dict(index=i,streams=streams,line_length=f[3],frame_length=f[4],output_pixel_clock=f[7],
   fps=fps,lane_count=f[11],three_phase=f[15],register_records=len(decoded)))
 initinfo=qwords(unique('initSettings'),'initSettings');assert len(initinfo)==3
 init=regs(initinfo[2],initinfo[1])
 report=dict(module=module,source_sha256=hashlib.sha256(data).hexdigest(),source_bytes=len(data),
  symbols=len(entries),all_symbol_payload_bounds_verified=True,init_register_records=len(init),mode_count=len(modes),modes=modes,
  operation_counts={op:sum(r['operation']==op for r in init) for op in operations[:-1]},
  operation_names_from_matching_schema=True,register_data_and_delays_uint32_vectors_with8byte_alignment=True,
  no_reader_execution=True,no_phone_operation=True,physical_module_variant_not_proven=True)
 (P/('gw1-'+module+'-direct-registers-private.json')).write_text(json.dumps(dict(init=init,modes=registers),indent=2)+'\n')
 reports.append(report)
result=dict(stage=270,modules=reports,hardware_not_supported_yet=True,independent_xml_crosscheck_pending=True)
(R/'gw1-metadata-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
