"""Two schema projections plus bounded original-BIN register decoding; no hardware access."""
from pathlib import Path
import hashlib,json,math,os,resource,shutil,signal,struct,subprocess,sys,xml.etree.ElementTree as ET
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel239');OLD=Path('/home/cy122/x2pro-linux/parser-k117')
source=Path('/mnt/e/edk2-samurai-out/kernel115/vendor-camera-bins/com.qti.sensormodule.qtech_s5k3m5sx.bin');original=source.read_bytes()
assert len(original)==383232 and original.startswith(b'QTI Chromatix Header\0') and struct.unpack_from('<I',original,28)[0]==len(original)
table,count=struct.unpack_from('<II',original,0x98);assert (table,count)==(0xa0,3)
sections=[struct.unpack_from('<QQQ',original,table+i*24) for i in range(count)]
assert sections==[(0,232,258552),(1,258784,124424),(2,383208,24)]
_,so,ss=sections[0];_,dataoff,datasize=sections[1];entries={}
for position in range(so,so+ss,72):
 ident=struct.unpack_from('<Q',original,position)[0];name=original[position+8:position+40].split(b'\0')[0].decode('ascii');relative,size=struct.unpack_from('<QQ',original,position+56)
 assert ident not in entries and relative+size<=datasize
 entries[ident]=dict(name=name,relative=relative,size=size,position=position)
def payload(ident,name):
 item=entries[ident];assert item['name']==name and item['relative']+item['size']<=datasize
 return original[dataoff+item['relative']:dataoff+item['relative']+item['size']]
def qwords(ident,name):
 data=payload(ident,name);assert len(data)%8==0
 return struct.unpack('<'+'Q'*(len(data)//8),data)
assert entries[1]['name']=='sensorDriverData' and entries[1]['size']==816
assert qwords(16,'resolutionInfo')==(1,17,4,18) and qwords(735,'initSettings')==(0,917,736)
def decode_regs(ident,n):
 data=payload(ident,'regSetting');assert len(data)==n*80
 rows=[]
 for offset in range(0,len(data),80):
  row=struct.unpack_from('<10Q',data,offset);assert row[0]==0 and row[3]==row[8]==1 and row[5]==2 and row[6] in [1,2] and row[7]==0
  values=qwords(row[4],'registerData');delays=qwords(row[9],'delayUs');assert len(values)==len(delays)==1
  assert 0<=row[2]<=65535 and 0<=values[0]<(1<<(8*row[6])) and 0<=delays[0]<=1000000
  rows.append((row[2],row[5],row[6],'WRITE',values,delays))
 return rows
def xml_regs(node):
 result=[]
 for row in node.findall('regSetting'):
  result.append((int(row.findtext('registerAddr')),int(row.findtext('regAddrType')),int(row.findtext('regDataType')),row.findtext('operation'),
                 tuple(int(x.text) for x in row.findall('registerData')),tuple(int(x.text) for x in row.findall('delayUs'))))
 return result
init=decode_regs(736,917);assert init[916]==(0x0101,2,1,'WRITE',(0,),(0,)) and init[5]==(0x0a02,2,2,'WRITE',(0x7800,),(5,))
assert all(row[2]==2 for row in init[:916])
mode_data=payload(18,'resolutionData');assert len(mode_data)==4*256
direct=[]
for i in range(4):
 fields=struct.unpack_from('<32Q',mode_data,i*256);assert fields[18]==53
 direct.append(dict(fields=fields,registers=decode_regs(fields[19],53)))
def limits():
 resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2));resource.setrlimit(resource.RLIMIT_CPU,(5,5));resource.setrlimit(resource.RLIMIT_FSIZE,(16*1024**2,16*1024**2))
resume=sys.argv[1:]==['--resume-existing-readers'];assert not sys.argv[1:] or resume
if resume:
 assert json.loads((R/'s5k3m5-first-validation-failure.json').read_text())['reader_exit_assertions_reached_before_init_shape_error']
 for proc in Path('/proc').glob('[0-9]*'):
  try:
   if (proc/'comm').read_text().strip()=='ParameterParser':assert 'parser-k239-s5k3m5' not in str((proc/'cwd').resolve())
  except (FileNotFoundError,ProcessLookupError):pass
reports={};xml_roots={}
for label,with_init,base in [('A',False,'parser-k235-imx319-qtech'),('B',True,'parser-k235-imx319-init-qtech')]:
 work=Path('/home/cy122/x2pro-linux')/('parser-k239-s5k3m5-'+label.lower())
 if resume:assert work.is_dir()
 else:assert not work.exists();work.mkdir(mode=0o700)
 schema=work/'api/sensor'
 if not resume:schema.parent.mkdir();shutil.copytree(Path('/home/cy122/x2pro-linux')/base/'api/sensor',schema)
 ns={'x':'http://www.w3.org/2001/XMLSchema'};tree=ET.parse(schema/'camxsensordriver.xsd');fields=tree.find("./x:complexType[@name='SensorDriverData']/x:sequence",ns)
 assert [e.attrib['name'] for e in fields]==['module_version','slaveInfo','resolutionInfo']+(['initSettings'] if with_init else [])
 driver=entries[1];start=dataoff+driver['relative'];projection=original[start:start+128]+struct.pack('<QQ',1,16)+(struct.pack('<QQ',1,735) if with_init else b'')
 assert len(projection)==(160 if with_init else 144)
 data=bytearray(original);relative=len(data)-dataoff;assert relative==124448
 data.extend(projection);allowed=set(range(28,32))|set(range(0xc8,0xd0))
 struct.pack_into('<I',data,28,len(data));struct.pack_into('<Q',data,0xc8,len(data)-dataoff)
 for item in entries.values():
  position=item['position']
  if item['name']=='sensorDriverData':struct.pack_into('<QQ',data,position+56,relative,len(projection));allowed.update(range(position+56,position+72))
  elif item['name']=='moduleConfiguration':struct.pack_into('<Q',data,position+64,72);allowed.update(range(position+64,position+72))
  elif struct.unpack_from('<I',data,position+40)[0]==1 and item['name']!='cameraModuleData':struct.pack_into('<I',data,position+40,0);allowed.update(range(position+40,position+44))
 assert all(i in allowed for i,(a,b) in enumerate(zip(original,data)) if a!=b)
 assert data[dataoff:dataoff+datasize]==original[dataoff:dataoff+datasize] and data[383208:383232]==bytes(24)
 assert len(data)==(383392 if with_init else 383376)
 analysis=work/'analysis.bin';dest=work/'xml'
 if resume:assert analysis.read_bytes()==data and dest.is_dir()
 else:
  analysis.write_bytes(data);dest.mkdir()
  for p in [work,*work.rglob('*')]:os.chown(p,1000,1000)
 timed=False
 if resume:
  assert (P/('s5k3m5-'+label.lower()+'-reader-private.log')).is_file()
  reader_exit=0 # Original run passed its exit assertion before the shape error.
 else:
  with (P/('s5k3m5-'+label.lower()+'-reader-private.log')).open('xb') as log:
   process=subprocess.Popen(['stdbuf','-oL','-eL',str(OLD/'ParameterParser'),str(dest),'x',str(schema),'-b'+str(analysis)],cwd=work,
                            env=dict(os.environ,LD_LIBRARY_PATH=str(OLD/'runtime/lib')),user=1000,group=1000,start_new_session=True,
                            stdin=subprocess.DEVNULL,stdout=log,stderr=log,preexec_fn=limits)
   try:process.wait(timeout=8)
   except subprocess.TimeoutExpired:timed=True;os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=3)
  reader_exit=process.returncode
 assert not timed and reader_exit==0,'inspect retained reader log and projection, do not overwrite'
 found=list(dest.rglob('sensorDriverData.xml'));assert len(found)==1
 xml=ET.parse(found[0]).getroot();modes=xml.findall('resolutionInfo/resolutionData');assert len(modes)==4
 public_modes=[]
 for i,node in enumerate(modes):
  fields=direct[i]['fields'];assert xml_regs(node.find('resSettings'))==direct[i]['registers']
  keys={'lineLengthPixelClock':3,'frameLengthLines':4,'minHorizontalBlanking':5,'minVerticalBlanking':6,'outputPixelClock':7,'horizontalBinning':8,'verticalBinning':9,'laneCount':11,'settleTimeNs':14,'is3Phase':15}
  assert all(int(node.findtext(key))==fields[position] for key,position in keys.items())
  fps=struct.unpack('<d',struct.pack('<Q',fields[10]))[0];assert math.isclose(float(node.findtext('frameRate')),fps,abs_tol=1e-6)
  streams=payload(fields[2],'streamConfiguration');assert len(streams)==fields[1]*64
  xml_streams=node.findall('streamInfo/streamConfiguration');assert len(xml_streams)==fields[1]
  dimensions=[]
  for index,stream_node in enumerate(xml_streams):
   q=struct.unpack_from('<8Q',streams,index*64)
   assert [int(stream_node.findtext(path)) for path in ['vc','dt','frameDimension/xStart','frameDimension/yStart','frameDimension/width','frameDimension/height','bitWidth']]==list(q[:7])
   dimensions.append(dict(vc=q[0],dt=q[1],width=q[4],height=q[5],bits=q[6]))
  public_modes.append(dict(index=i,streams=dimensions,line_length=fields[3],frame_length=fields[4],lane_count=fields[11],output_pixel_clock_metadata=fields[7],fps_metadata=fps,register_records=53))
 if with_init:
  groups=xml.findall('initSettings/initSetting');assert len(groups)==1
  assert xml_regs(groups[0])==init
 else:assert xml.find('initSettings') is None
 target=P/('s5k3m5-'+label.lower()+'-xml-private')
 if target.exists():
  assert resume
  assert {str(p.relative_to(dest)):p.read_bytes() for p in dest.rglob('*') if p.is_file()}=={str(p.relative_to(target)):p.read_bytes() for p in target.rglob('*') if p.is_file()}
 else:shutil.copytree(dest,target)
 assert source.read_bytes()==original
 xml_roots[label]=modes
 reports[label]=dict(reader_exit=reader_exit,timed_out=False,reader_not_reexecuted_on_xml_shape_fix=resume,projection_bytes=len(projection),projected_file_bytes=len(data),driver_relative_from_eof=relative,
                    original_payload_unchanged=True,original_section2_tail_preserved=True,all_original_byte_changes_within_allowed_header_symbol_fields=True,
                    mode_count=4,mode_register_records=212,init_register_records=917 if with_init else 0,modes=public_modes)
for a,b in zip(xml_roots['A'],xml_roots['B']):assert ET.tostring(a)==ET.tostring(b)
(P/'s5k3m5-direct-registers-private.json').write_text(json.dumps(dict(init=init,modes=[d['registers'] for d in direct]),indent=2)+'\n')
report=dict(stage=239,original_bin_unchanged=True,two_schema_projections_of_one_qtech_source=True,independent_bounded_original_bin_decoder_agrees=True,
            both_mode_xml_outputs_equal=True,mode_register_records_verified=212,init_register_records_verified=917,init_last_write8_preserved=True,init_row5_delay5_microseconds_preserved=True,
            duplicate_register_writes_not_deduplicated=True,reader_uid_gid1000_address_space256m_cpu5s_wall8s_file16m=True,analysis_projection_not_product_bin=True,
            no_phone_or_power_operation=True,physical_s5k3m5_capture_not_yet_verified=True,projections=reports)
(R/'s5k3m5-crosscheck-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
