"""Compare the independent XML parser's commands and tuning against the bounded decoder."""
from pathlib import Path
import hashlib,json,xml.etree.ElementTree as ET
import host
R=Path(__file__).resolve().parent;proof=json.loads((R/'actuator-contract-validation.json').read_text());rows=[]
for expected in proof['variants']:
 p=host.PRIVATE/('actuator-'+expected['variant']+'-xml-r1-private.xml');b=p.read_bytes();xml=ET.fromstring(b)
 reg=[dict(address_bytes=int(x.findtext('regAddrType')),value_bytes=int(x.findtext('regDataType')),address=int(x.findtext('registerAddr')),base_data=int(x.findtext('registerData')),operation=x.findtext('operation'),delay_us=int(x.findtext('delayUs')),hw_mask=int(x.findtext('hwMask')),hw_shift=int(x.findtext('hwShift')),data_shift=int(x.findtext('dataShift'))) for x in xml.findall('registerConfig/registerParam')]
 init=[dict(address=int(x.findtext('registerAddr')),address_bytes=int(x.findtext('regAddrType')),value_bytes=int(x.findtext('regDataType')),value=int(x.findtext('registerData')),delay_us=int(x.findtext('delayUs'))) for x in xml.findall('initSettings/regSetting')]
 assert all(x.findtext('operation')=='WRITE' for x in xml.findall('initSettings/regSetting'))
 assert reg==expected['position_write'] and init==expected['initialization']
 assert int(xml.findtext('tunedParams/initialCode'))==expected['tuned_initial_code']
 regions=[dict(macro_step_boundary=int(x.findtext('macroStepBoundary')),infinity_step_boundary=int(x.findtext('infinityStepBoundary')),code_per_step=float(x.findtext('codePerStep')),q_value=int(x.findtext('qValue'))) for x in xml.findall('tunedParams/regionParams/region')]
 assert regions==expected['regions']
 power={}
 for name,key in [('powerUpSequence','up'),('powerDownSequence','down')]:
  settings=xml.findall('slaveInfo/'+name+'/powerSetting');assert all(x.findtext('configType')=='VAF' for x in settings)
  power[key]=[[4,int(x.findtext('configValue')),int(x.findtext('delayMs'))] for x in settings]
 assert power==expected['power_sequence_raw']
 damping={}
 for direction in ['forward','backward']:
  damping[direction]=[{key:int(x.findtext(key)) for key in ['dampingStep','dampingDelayUs','hwParams']} for x in xml.findall('tunedParams/'+direction+'Damping/scenarioDampingParams/scenario/region')]
 rows.append(dict(variant=expected['variant'],position_initialization_power_tuning_match=True,damping=damping,xml_sha256=hashlib.sha256(b).hexdigest()))
out=dict(stage=274,variants=rows,independent_xml_and_direct_decoder_agree=True,no_phone_operation=True)
(R/'actuator-command-crosscheck-validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
