"""Decode actuator commands from the two fixed handset descriptions, not filename guesses."""
from pathlib import Path
import hashlib,json,struct,sys,xml.etree.ElementTree as ET
import host
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'kernel272'))
from gw1_data import Description
R=Path(__file__).resolve().parent
schema=ET.parse('/mnt/e/edk2-samurai-out/kernel117/CamxChi/chi-cdk/api/sensor/camxactuatordriver.xsd');ns={'x':'http://www.w3.org/2001/XMLSchema'}
operations=[x.attrib['value'] for x in schema.findall("./x:simpleType[@name='ActuatorOperation']/x:restriction/x:enumeration",ns)]
assert operations==['WRITE_HW_DAMP','WRITE_DAC_VALUE','WRITE','WRITE_DIR_REG','POLL','READ_WRITE']
rows=[]
for variant in ['sunny','qtech']:
 d=Description(variant);w=d.words(d.uid('actuatorDriver'));assert len(w)==28 and list(w[:3])==[1,0,0]
 name=d.payload(w[4],'actuatorName').split(b'\0')[0].decode();assert w[3]==len(name)+1
 powers={}
 for label,off in [('up',9),('down',11)]:
  p=d.payload(w[off+1],'powerSetting');assert len(p)==w[off]*24
  powers[label]=[list(struct.unpack_from('<3Q',p,i*24)) for i in range(w[off])]
 raw=d.payload(w[14],'registerParam');assert len(raw)==w[13]*72;params=[]
 for i in range(w[13]):
  f=struct.unpack_from('<9Q',raw,i*72);assert f[0] in [1,2] and f[1] in [1,2] and f[4]<len(operations)
  params.append(dict(address_bytes=f[0],value_bytes=f[1],address=f[2],base_data=f[3],operation=operations[f[4]],delay_us=f[5],hw_mask=f[6],hw_shift=f[7],data_shift=f[8]))
 raw=d.payload(w[16],'regSetting');assert len(raw)==w[15]*80;initial=[]
 for i in range(w[15]):
  f=struct.unpack_from('<10Q',raw,i*80);assert f[0]==0 and f[3]==f[8]==1 and f[5] in [1,2] and f[6] in [1,2] and f[7]==0
  v=d.words(f[4],'registerData');delay=d.words(f[9],'delayUs');assert len(v)==len(delay)==1
  initial.append(dict(address=f[2],address_bytes=f[5],value_bytes=f[6],value=v[0],delay_us=delay[0]))
 assert w[17]==0 and not d.payload(w[18],'deInitSettings')
 raw=d.payload(w[21],'region');assert len(raw)==w[20]*32;regions=[]
 for i in range(w[20]):
  f=struct.unpack_from('<4Q',raw,i*32)
  regions.append(dict(macro_step_boundary=f[0],infinity_step_boundary=f[1],code_per_step=struct.unpack('<f',struct.pack('<I',f[2]&0xffffffff))[0],q_value=f[3]))
 rows.append(dict(variant=variant,source_sha256=hashlib.sha256(d.raw).hexdigest(),name=name,address8=w[5],address7=w[5]>>1,
  i2c_frequency_mode=w[6],actuator_type=w[7],data_bit_width=w[8],power_sequence_raw=powers,
  position_write=params,initialization=initial,tuned_initial_code=w[19],regions=regions,
  module_eeprom_calibration_may_override_tuned_defaults=True))
(host.PRIVATE/'actuator-decoded-candidate-private.json').write_text(json.dumps(rows,indent=2)+'\n')
assert rows[0]['name']=='s5kgw1_lc898219xi' and rows[0]['address7']==0x72
assert rows[0]['position_write']==[dict(address_bytes=1,value_bytes=2,address=0x84,base_data=0,operation='WRITE_DAC_VALUE',delay_us=1,hw_mask=0,hw_shift=0,data_shift=0)]
assert rows[0]['initialization']==[dict(address=0xe0,address_bytes=1,value_bytes=1,value=1,delay_us=1)]
out=dict(stage=274,variants=rows,source_headers_and_vector_bounds_verified=True,operation_enum_from_matching_schema=True,
 actual_handset_actuator_model_not_yet_proven=True,no_actuator_operation=True,
 lc898219xi_datasheet='https://www.onsemi.com/download/data-sheet/pdf/lc898219xi-d.pdf',
 datasheet_vdd_range_volts=[2.6,3.3],datasheet_nominal_vdd_volts=2.8,
 datasheet_power_on_to_i2c_min_us=5000,datasheet_power_off_min_us=100000,
 public_datasheet_does_not_include_register_map=True)
(R/'actuator-contract-validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
