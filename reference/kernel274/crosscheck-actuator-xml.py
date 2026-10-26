"""Independently decode both actuator sections with the retained bounded OEM parser."""
from pathlib import Path
import hashlib,json,os,resource,shutil,signal,struct,subprocess,xml.etree.ElementTree as ET
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE
proof=json.loads((R/'actuator-contract-validation.json').read_text());rows=[]
old=Path('/home/cy122/x2pro-linux/parser-k117');ns={'x':'http://www.w3.org/2001/XMLSchema'}
def limits():
 resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2));resource.setrlimit(resource.RLIMIT_CPU,(15,15));resource.setrlimit(resource.RLIMIT_FSIZE,(64*1024**2,64*1024**2))
for expected in proof['variants']:
 variant=expected['variant'];work=Path('/home/cy122/x2pro-linux')/('parser-k274-actuator-'+variant+'-r1');work.mkdir(mode=0o700)
 schema=work/'api/sensor';schema.parent.mkdir();schema.mkdir()
 source=Path('/mnt/e/edk2-samurai-out/kernel117/CamxChi/chi-cdk/api/sensor')
 for name in ['camxactuatordriver.xsd','camxsensorcommon.xsd']:shutil.copyfile(source/name,schema/name)
 # This older binary schema predates the optional actuatorID field. No payload is changed.
 tree=ET.parse(schema/'camxactuatordriver.xsd');sequence=tree.find("./x:complexType[@name='ActuatorSlaveInfo']/x:sequence",ns)
 field=sequence.find("x:element[@name='actuatorID']",ns);assert field is not None and field.attrib['minOccurs']=='0';sequence.remove(field);tree.write(schema/'camxactuatordriver.xsd')
 original=Path('/mnt/e/edk2-samurai-out/kernel115/vendor-camera-bins')/('com.qti.sensormodule.'+variant+'_s5kgw1.bin');b=original.read_bytes();assert hashlib.sha256(b).hexdigest()==expected['source_sha256']
 data=bytearray(b);table,count=struct.unpack_from('<II',b,0x98);sections=[struct.unpack_from('<QQQ',b,table+i*24) for i in range(count)]
 _,offset,size=sections[0];allowed=set();roots=[]
 for pos in range(offset,offset+size,72):
  name=b[pos+8:pos+40].split(b'\0')[0].decode();flag=struct.unpack_from('<I',b,pos+40)[0]
  if flag==1:
   roots.append(name)
   if name!='actuatorDriver':struct.pack_into('<I',data,pos+40,0);allowed.update(range(pos+40,pos+44))
 assert 'actuatorDriver' in roots and all(i in allowed for i,(x,y) in enumerate(zip(b,data)) if x!=y)
 for _,off,size in sections[1:]:assert data[off:off+size]==b[off:off+size]
 analysis=work/'analysis.bin';analysis.write_bytes(data);dest=work/'xml';dest.mkdir()
 for p in [work,*work.rglob('*')]:os.chown(p,1000,1000)
 logfile=P/('actuator-'+variant+'-reader-r1-private.log')
 with logfile.open('xb') as log:
  proc=subprocess.Popen(['stdbuf','-oL','-eL',str(old/'ParameterParser'),str(dest),'x',str(schema),'-b'+str(analysis)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=str(old/'runtime/lib')),user=1000,group=1000,start_new_session=True,stdin=subprocess.DEVNULL,stdout=log,stderr=log,preexec_fn=limits)
  try:ret=proc.wait(timeout=20)
  except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=3);raise RuntimeError('Bounded offline parser timed out; inspect retained output')
 (P/('actuator-'+variant+'-reader-r1-exit-private.json')).write_text(json.dumps(dict(pid=proc.pid,exit=ret,terminal=True))+'\n')
 assert ret==0,'Inspect private reader output; no phone operation was performed'
 found=list(dest.rglob('actuatorDriver.xml'));assert len(found)==1
 xml=ET.parse(found[0]).getroot();(P/('actuator-'+variant+'-xml-r1-private.xml')).write_bytes(ET.tostring(xml))
 slave=xml.find('slaveInfo');assert slave is not None
 assert slave.findtext('actuatorName')==expected['name'] and int(slave.findtext('slaveAddress'))==expected['address8']
 assert int(slave.findtext('dataBitWidth'))==expected['data_bit_width']
 # The independent XML hierarchy is retained; initial command and position fields are compared next.
 rows.append(dict(variant=variant,parser_exit=ret,name_address_width_match=True,xml_sha256=hashlib.sha256(ET.tostring(xml)).hexdigest(),source_unchanged=original.read_bytes()==b))
out=dict(stage=274,variants=rows,bounded_parser_uid1000_memory256m_cpu15s_wall20s=True,original_payload_sections_unchanged=True,no_phone_operation=True)
(R/'actuator-xml-crosscheck-validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
