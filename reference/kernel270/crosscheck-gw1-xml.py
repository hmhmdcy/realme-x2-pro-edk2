"""Cross-check both GW1 descriptions with two bounded schema projections each."""
from pathlib import Path
import hashlib,json,os,resource,shutil,signal,struct,subprocess,sys,xml.etree.ElementTree as ET
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel270');OLD=Path('/home/cy122/x2pro-linux/parser-k117')
attempt=int(sys.argv[1]) if sys.argv[1:] else 1;assert attempt in [1,2]
metadata=json.loads((R/'gw1-metadata-validation.json').read_text());results=[]
def limits():
 resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2));resource.setrlimit(resource.RLIMIT_CPU,(15,15));resource.setrlimit(resource.RLIMIT_FSIZE,(64*1024**2,64*1024**2))
def xml_regs(parent):
 result=[]
 for row in parent.findall('regSetting'):
  vals=lambda name:[int(v) for e in row.findall(name) for v in (e.text or '').split()]
  result.append(dict(address=int(row.findtext('registerAddr')),address_bytes=int(row.findtext('regAddrType')),
   value_bytes=int(row.findtext('regDataType')),operation=row.findtext('operation'),values=vals('registerData'),delays_us=vals('delayUs')))
 return result
for info in metadata['modules']:
 module=info['module'];path=Path('/mnt/e/edk2-samurai-out/kernel115/vendor-camera-bins')/('com.qti.sensormodule.'+module+'_s5kgw1.bin')
 original=path.read_bytes();assert hashlib.sha256(original).hexdigest()==info['source_sha256']
 table,count=struct.unpack_from('<II',original,0x98);sections=[struct.unpack_from('<QQQ',original,table+i*24) for i in range(count)]
 _,so,ss=sections[0];_,dataoff,datasize=sections[1];entries={}
 for pos in range(so,so+ss,72):
  ident=struct.unpack_from('<Q',original,pos)[0];name=original[pos+8:pos+40].split(b'\0')[0].decode();off,size=struct.unpack_from('<QQ',original,pos+56)
  entries[ident]=dict(name=name,relative=off,size=size,position=pos)
 def uid(name):
  found=[i for i,row in entries.items() if row['name']==name];assert len(found)==1;return found[0]
 driver=entries[uid('sensorDriverData')];assert driver['size']==816
 direct=json.loads((P/('gw1-'+module+'-direct-registers-private.json')).read_text());mode_views=[]
 for label,with_init,template in [('a',False,'parser-k235-imx319-qtech'),('b',True,'parser-k235-imx319-init-qtech')]:
  suffix='-r'+str(attempt) if attempt>1 else ''
  work=Path('/home/cy122/x2pro-linux')/('parser-k270-gw1-'+module+'-'+label+suffix);work.mkdir(mode=0o700)
  schema=work/'api/sensor';schema.parent.mkdir();shutil.copytree(Path('/home/cy122/x2pro-linux')/template/'api/sensor',schema)
  start=dataoff+driver['relative'];projection=original[start:start+128]+struct.pack('<QQ',1,uid('resolutionInfo'))
  if with_init:projection+=struct.pack('<QQ',1,uid('initSettings'))
  data=bytearray(original);relative=len(data)-dataoff;data.extend(projection)
  allowed=set(range(28,32))|set(range(table+24+16,table+24+24))
  struct.pack_into('<I',data,28,len(data));struct.pack_into('<Q',data,table+24+16,len(data)-dataoff)
  for row in entries.values():
   pos=row['position']
   if row['name']=='sensorDriverData':struct.pack_into('<QQ',data,pos+56,relative,len(projection));allowed.update(range(pos+56,pos+72))
   elif row['name']=='moduleConfiguration':struct.pack_into('<Q',data,pos+64,72);allowed.update(range(pos+64,pos+72))
   elif struct.unpack_from('<I',data,pos+40)[0]==1 and row['name']!='cameraModuleData':struct.pack_into('<I',data,pos+40,0);allowed.update(range(pos+40,pos+44))
  assert all(i in allowed for i,(a,b) in enumerate(zip(original,data)) if a!=b)
  assert data[dataoff:dataoff+datasize]==original[dataoff:dataoff+datasize]
  assert data[sections[2][1]:sections[2][1]+sections[2][2]]==original[sections[2][1]:sections[2][1]+sections[2][2]]
  analysis=work/'analysis.bin';analysis.write_bytes(data);dest=work/'xml';dest.mkdir()
  for p in [work,*work.rglob('*')]:os.chown(p,1000,1000)
  logfile=P/('gw1-'+module+'-'+label+suffix+'-reader-private.log')
  with logfile.open('xb') as log:
   proc=subprocess.Popen(['stdbuf','-oL','-eL',str(OLD/'ParameterParser'),str(dest),'x',str(schema),'-b'+str(analysis)],cwd=work,
    env=dict(os.environ,LD_LIBRARY_PATH=str(OLD/'runtime/lib')),user=1000,group=1000,start_new_session=True,
    stdin=subprocess.DEVNULL,stdout=log,stderr=log,preexec_fn=limits)
   try:ret=proc.wait(timeout=20)
   except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=3);raise RuntimeError('Bounded GW1 reader timed out; retain output and inspect')
  (P/('gw1-'+module+'-'+label+suffix+'-reader-exit-private.json')).write_text(json.dumps(dict(pid=proc.pid,exit=ret,terminal=True))+'\n')
  assert ret==0,'Inspect retained GW1 reader log; no hardware was touched'
  found=list(dest.rglob('sensorDriverData.xml'));assert len(found)==1;xml=ET.parse(found[0]).getroot()
  modes=xml.findall('resolutionInfo/resolutionData');assert len(modes)==info['mode_count']
  for i,node in enumerate(modes):assert xml_regs(node.find('resSettings'))==direct['modes'][i],(module,label,i)
  if with_init:
   groups=xml.findall('initSettings/initSetting');assert len(groups)==1 and xml_regs(groups[0])==direct['init']
  else:assert xml.find('initSettings') is None
  mode_views.append([ET.tostring(n) for n in modes])
  results.append(dict(module=module,projection=label,reader_exit=ret,mode_count=len(modes),
   init_records_checked=info['init_register_records'] if with_init else 0,
   modes_and_uint32_burst_vectors_match_independent_decoder=True,original_source_unchanged=path.read_bytes()==original))
 assert mode_views[0]==mode_views[1]
report=dict(stage=270,results=results,both_module_variants_crosschecked=True,two_views_each=True,
 readonly_original_inputs=True,reader_uid_gid1000_memory256m_cpu15s_wall20s_file64m=True,
 metadata_only_not_physical_sensor_identification=True,no_phone_or_power_operation=True)
(R/'gw1-crosscheck-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
