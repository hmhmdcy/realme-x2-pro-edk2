"""Decode retained AWB reference/golden/MWB roots and compare stock XML output."""
from pathlib import Path
import hashlib, json, math, os, struct, subprocess, xml.etree.ElementTree as ET
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
repo=Path('/home/cy122/x2pro-linux/refs/CamxChi-k117')
commit=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
assert commit=='9f17f1b568626b393e785b369c5dc94543774d7a'
schema_paths=['stats/awb/'+n for n in ['modsensorcalv1.xsd','modrefptv1.xsd','modmwbv1.xsd','awbglobalelements.xsd']]
schema_paths+=['common/globalelements.xsd','ParameterTuningTypes.xsd']
schemas={}
for n in schema_paths:
 cached=P.parent/'kernel117/CamxChi/chi-cdk/api/chromatix/XSD'/n
 if cached.exists():
  contents=cached.read_bytes()
  expected=subprocess.check_output(['git','-C',str(repo),'rev-parse',commit+':chi-cdk/api/chromatix/XSD/'+n],text=True).strip()
  assert hashlib.sha1(b'blob '+str(len(contents)).encode()+b'\0'+contents).hexdigest()==expected
 else:contents=subprocess.check_output(['git','-C',str(repo),'show',commit+':chi-cdk/api/chromatix/XSD/'+n])
 schemas[n]=contents
# Reuse the common mode-selector schema already matched to these OEM bins in324.
schemas['common/globalelements.xsd']=(P.parent/'kernel298/globalelements.xsd-reference-private').read_bytes()
sources=[dict(path='chi-cdk/api/chromatix/XSD/'+n,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),
 repository='https://github.com/comprehensive9/vendor_qcom_proprietary' if n=='common/globalelements.xsd' else 'https://github.com/bjzhou/CamxChi',
 source_stage=298 if n=='common/globalelements.xsd' else 117,
 commit='36fc163a534963a5b3af52186af5efcc63401ad2' if n=='common/globalelements.xsd' else commit) for n,raw in schemas.items()]
tags={'sensorCalV1','refPtV1','MWBGainV1'}
reports=[]
def normalize(value):
 if isinstance(value,float):return float(format(value,'.6g'))
 if isinstance(value,list):return [normalize(x) for x in value]
 if isinstance(value,dict):return {k:normalize(v) for k,v in value.items()}
 return value
for name,stage,filename in [('qtech_s5kgw1',324,'qtech_s5kgw1-tuning-private.bin'),
 ('sunny_s5kgw1',324,'sunny_s5kgw1-tuning-private.bin'),('sunny_imx471',324,'sunny_imx471-tuning-private.bin'),
 ('qtech_s5k3m5sx',306,'qtech-s5k3m5sx-tuning-private.bin'),('sunny_imx319',298,'sunny-imx319-tuning-private.bin')]:
 raw=(P.parent/('kernel'+str(stage))/filename).read_bytes();table,count=struct.unpack_from('<II',raw,0x98)
 sections=[struct.unpack_from('<QQQ',raw,table+i*24) for i in range(count)]
 start,length=sections[0][1:];base,size=sections[1][1:]
 analysis=bytearray(raw);roots=[];calibration_layouts=[]
 for pos in range(start,start+length,72):
  uid=struct.unpack_from('<Q',raw,pos)[0];tag=raw[pos+8:pos+40].split(b'\0')[0].decode()
  version=struct.unpack_from('<I',raw,pos+40)[0];offset,n=struct.unpack_from('<QQ',raw,pos+56)
  assert offset+n<=size
  if not version:continue
  if tag=='sensorCalV1':
   calibration_layouts.append(dict(uid=uid,observed_bytes=n,public_schema_bytes=320,
    cct_array_elements=6,cct_array_element_bytes=4,compatible=n==320))
  if tag not in tags:struct.pack_into('<I',analysis,pos+40,0);continue
  data=raw[base+offset:base+offset+n]
  word=lambda i:struct.unpack_from('<Q',data,i*8)[0]
  number=lambda i:struct.unpack_from('<f',data,i*8)[0]
  assert n==(320 if tag=='sensorCalV1' else 288)
  result=dict(module_id=word(0),submodule_id=word(1),revision=[word(i) for i in range(2,5)],enabled=word(5))
  if tag=='sensorCalV1':
   result.update(num_of_cal_factors=word(6),cct=list(struct.unpack_from('<6f',data,56)),
    points=[[number(10+i*2+j) for j in range(2)] for i in range(15)])
  elif tag=='refPtV1':result['points']=[[number(6+i*2+j) for j in range(2)] for i in range(15)]
  else:result['gains']=[[number(6+i*3+j) for j in range(3)] for i in range(10)]
  # Unused slots are allowed to be zero; preserve them instead of repairing data.
  assert all(math.isfinite(v) for row in result.get('points',result.get('gains')) for v in row)
  roots.append(dict(uid=uid,tag=tag,data=result))
 (P/(name+'-factory-wb-private.json')).write_text(json.dumps(roots,indent=2)+'\n')
 work=Path('/home/cy122/x2pro-linux')/('parser-k328-'+name+'-wb-r4')
 schema=work/'api/stats/awb';dest=work/'xml'
 if not work.exists():
  work.mkdir(mode=0o700)
  for relative,contents in schemas.items():
   target=work/'api'/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(contents)
  (schema/'ParameterTuningTypes.xsd').write_bytes(schemas['ParameterTuningTypes.xsd'])
  (work/'analysis.bin').write_bytes(analysis);dest.mkdir()
  for item in [work,*work.rglob('*')]:os.chown(item,1000,1000)
 else:assert (work/'analysis.bin').read_bytes()==analysis
 exit_path=P/(name+'-parser-r4-exit.json')
 if not exit_path.exists():
  reader=Path('/home/cy122/x2pro-linux/parser-k117')
  with (P/(name+'-parser-r4.log')).open('xb') as log:
   q=subprocess.run(['stdbuf','-oL','-eL',str(reader/'ParameterParser'),str(dest),'x',str(schema),'-b'+str(work/'analysis.bin')],cwd=work,
    env=dict(os.environ,LD_LIBRARY_PATH=str(reader/'runtime/lib')),user=1000,group=1000,stdin=subprocess.DEVNULL,stdout=log,stderr=log,timeout=55)
  exit_path.write_text(json.dumps(dict(exit_code=q.returncode)))
  assert not q.returncode,(name,q.returncode)
 else:
  assert not json.loads(exit_path.read_text())['exit_code']
 records=[]
 for path in dest.rglob('*.xml'):
  if path.stem not in tags:continue
  tree=ET.parse(path);xml=tree.getroot()
  result=dict(module_id=int(xml.findtext('moduleID/moduleID')),submodule_id=int(xml.findtext('moduleID/subModuleID')),
   revision=[int(xml.findtext('module_version/'+n)) for n in ['major_revision','minor_revision','incr_revision']],enabled=int(xml.findtext('enableFlag')))
  if path.stem=='sensorCalV1':
   result.update(num_of_cal_factors=int(xml.findtext('numOfCalFactors')),cct=[float(n.text) for n in xml.findall('cctOfCalFactors')],
    points=[[float(n.findtext(c)) for c in ['rg','bg']] for n in xml.findall('goldenModuleCal')])
  elif path.stem=='refPtV1':result['points']=[[float(n.findtext(c)) for c in ['rg','bg']] for n in xml.findall('refPt')]
  else:result['gains']=[[float(n.findtext(c)) for c in ['red','green','blue']] for n in xml.findall('MWBData')]
  matches=[r['uid'] for r in roots if r['tag']==path.stem and normalize(r['data'])==normalize(result)]
  assert matches,str(path)
  records.append(dict(selector=path.relative_to(dest).as_posix(),binary_uids=matches,all_values_match=True))
 assert len(records)==len(roots) and {r['uid'] for r in roots}=={u for r in records for u in r['binary_uids']},(name,len(records),len(roots),records)
 assert all(analysis[o:o+n]==raw[o:o+n] for _,o,n in sections[1:])
 reports.append(dict(module=name,roots={tag:sum(r['tag']==tag for r in roots) for tag in sorted(tags)},selectors=records,
  payload_and_mode_tree_unchanged=True,calibration_enabled_states=sorted({r['data']['enabled'] for r in roots if r['tag']=='sensorCalV1'}),
  calibration_factor_counts=sorted({r['data']['num_of_cal_factors'] for r in roots if r['tag']=='sensorCalV1'}),
  calibration_cct_slots=[r['data']['cct'] for r in roots if r['tag']=='sensorCalV1'],
  sensor_cal_layouts=calibration_layouts,sensor_cal_decoded=True,sensor_cal_applied=False,
  nonpositive_slots={tag:sum(v<=0 for r in roots if r['tag']==tag for row in r['data'].get('points',r['data'].get('gains')) for v in row) for tag in sorted(tags)}))
report=dict(stage=328,schema_repository='https://github.com/bjzhou/CamxChi',schema_commit=commit,schemas=sources,
 modules=reports,phone_changed=False,unit_white_balance_applied=False,passed=True)
(HERE/'factory-wb-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(stage=328,modules=[{k:v for k,v in r.items() if k!='selectors'} for r in reports],passed=True),indent=2))
