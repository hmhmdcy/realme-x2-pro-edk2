"""Cross-check all six bounded prefix decodes against the independent vendor reader.

Only private analysis copies are modified. No camera register tables are exported.
"""
from pathlib import Path
import os,struct,shutil,subprocess,resource,signal,json,xml.etree.ElementTree as ET,hashlib
OUT=Path('/mnt/e/edk2-samurai-out/kernel192');REF=Path(__file__).resolve().parent
WORK=Path('/home/cy122/x2pro-linux/parser-k192-batch');WORK.mkdir(mode=0o700)
OLD=Path('/home/cy122/x2pro-linux/parser-k117');SCHEMA=WORK/'api/sensor';SCHEMA.parent.mkdir(parents=True)
shutil.copytree(OLD/'api/sensor',SCHEMA)
NS={'x':'http://www.w3.org/2001/XMLSchema'};ET.register_namespace('xs',NS['x'])
for filename,complex_type,keep,expected in [
 ('camxsensordriver.xsd','SensorDriverData',2,['module_version','slaveInfo']),
 ('camxmoduleconfig.xsd','ModuleConfiguration',5,['cameraId','moduleName','sensorName','sensorSlaveAddress','sensorI2CFrequencyMode'])]:
 tree=ET.parse(SCHEMA/filename);seq=tree.find("./x:complexType[@name='"+complex_type+"']/x:sequence",NS)
 assert seq is not None and [e.attrib.get('name') for e in list(seq)[:keep]]==expected
 for node in list(seq)[keep:]:seq.remove(node)
 tree.write(SCHEMA/filename,encoding='utf-8',xml_declaration=True)
records=json.loads((OUT/'camera-prefix-decoded-private.json').read_text())['sensors'];report=[]
def limits():
 resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2));resource.setrlimit(resource.RLIMIT_CPU,(5,5));resource.setrlimit(resource.RLIMIT_FSIZE,(16*1024**2,16*1024**2))
for p in [WORK,*WORK.rglob('*')]:os.chown(p,1000,1000)
for record in records:
 source=Path('/mnt/e/edk2-samurai-out/kernel115/vendor-camera-bins')/record['file'];orig=source.read_bytes()
 assert hashlib.sha256(orig).hexdigest()==record['sha256'];b=bytearray(orig)
 _,so,ss=struct.unpack_from('<QQQ',b,0xa0)
 for off in range(so,so+ss,72):
  name=bytes(b[off+8:off+40]).split(b'\0')[0]
  if name==b'sensorDriverData':struct.pack_into('<Q',b,off+64,128)
  elif name==b'moduleConfiguration':struct.pack_into('<Q',b,off+64,72)
  elif struct.unpack_from('<I',b,off+40)[0]==1 and name!=b'cameraModuleData':struct.pack_into('<I',b,off+40,0)
 analysis=WORK/(record['file']+'.analysis');analysis.write_bytes(b);os.chown(analysis,1000,1000)
 dest=WORK/record['file'];dest.mkdir();os.chown(dest,1000,1000)
 args=['stdbuf','-oL','-eL',str(OLD/'ParameterParser'),str(dest),'x',str(SCHEMA),'-b'+str(analysis)]
 with (OUT/(record['file']+'-crosscheck-private.log')).open('xb') as log:
  proc=subprocess.Popen(args,cwd=WORK,env=dict(os.environ,LD_LIBRARY_PATH=str(OLD/'runtime/lib')),user=1000,group=1000,start_new_session=True,stdin=subprocess.DEVNULL,stdout=log,stderr=log,preexec_fn=limits)
  try:proc.wait(timeout=8)
  except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=3)
 assert proc.returncode==0 and source.read_bytes()==orig
 sensorxml=list(dest.rglob('sensorDriverData.xml'));modulexml=list(dest.rglob('cameraModuleData.xml'));assert len(sensorxml)==len(modulexml)==1
 sensor=ET.parse(sensorxml[0]).getroot().find('slaveInfo');assert sensor is not None
 for name,key in [('sensorName','sensor'),('slaveAddress','slave_address_8bit'),('regAddrType','reg_address_type'),('regDataType','reg_data_type'),('sensorIdRegAddr','id_register'),('sensorId','id_value'),('sensorIdMask','id_mask')]:
  actual=sensor.findtext(name);expected=record[key]
  assert (actual if isinstance(expected,str) else int(actual))==expected,(record['file'],name)
 freq=['STANDARD','FAST','CUSTOM','FAST_PLUS'];assert sensor.findtext('i2cFrequencyMode')==freq[record['i2c_frequency_enum']]
 for element,key in [('powerUpSequence','power_up'),('powerDownSequence','power_down')]:
  actual=[dict(type=n.findtext('configType'),value=int(n.findtext('configValue')),delay_ms=int(n.findtext('delayMs'))) for n in sensor.findall(element+'/powerSetting')]
  expected=[{k:x[k] for k in ['type','value','delay_ms']} for x in record[key]]
  assert actual==expected,(record['file'],key)
 module=ET.parse(modulexml[0]).getroot().find('moduleGroup/moduleConfiguration');assert module is not None
 assert int(module.findtext('cameraId'))==record['module']['camera_slot'] and module.findtext('sensorName')==record['sensor']
 assert module.find('sensorSlaveAddress') is None and module.find('sensorI2CFrequencyMode') is None
 report.append(dict(file=record['file'],sha256=record['sha256'],camera_slot=record['module']['camera_slot'],sensor=record['sensor'],i2c_address_7bit=record['i2c_address_7bit'],id_register=record['id_register'],id_value=record['id_value'],power_up_steps=len(record['power_up']),power_down_steps=len(record['power_down']),all_prefix_fields_match_independent_vendor_reader=True,source_unchanged=True))
validation=dict(stage=192,bins=report,source_bin_count=len(records),independent_vendor_reader_matches=6,sensor_prefix_bytes=128,module_prefix_bytes=72,full_sensor_register_parser_complete=False,calibration_or_eeprom_decoded=False,physical_sensor_id_read=False,physical_camera_accepted=False)
(REF/'camera-prefix-validation.json').write_text(json.dumps(validation,indent=2)+'\n');print(json.dumps(validation))
