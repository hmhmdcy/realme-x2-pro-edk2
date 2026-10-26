"""Decode full CCM topology and compare the retained OEM parser's XML."""
from pathlib import Path
import json,math,os,shutil,struct,subprocess,xml.etree.ElementTree as ET
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
levels=[('mod_cc12_drc_gain_data','drc_gain_trigger','drc_gain_data',['start','end']),
 ('mod_cc12_hdr_aec_data','hdr_aec_trigger','hdr_aec_data',['exp_time_start','exp_time_end','aec_sensitivity_start','aec_sensitivity_end','exp_gain_start','exp_gain_end']),
 ('mod_cc12_led_idx_data','led_idx_trigger','led_idx_data',['led_index']),
 ('mod_cc12_aec_data','aec_trigger','aec_data',['lux_idx_start','lux_idx_end','gain_start','gain_end'])]
def norm(v):
 if isinstance(v,float):return float(format(v,'.6g'))
 if isinstance(v,list):return [norm(x) for x in v]
 if isinstance(v,dict):return {k:norm(x) for k,x in v.items()}
 return v
reports=[]
for name in ['qtech_s5kgw1','sunny_s5kgw1','sunny_imx471','qtech_s5k3m5sx','sunny_imx319']:
 index=json.loads((P/(name+'-index-private.json')).read_text());entries=index['entries'];base=index['base']
 raw=(P.parent/('kernel'+str(index['source_stage']))/index['filename']).read_bytes()
 def blob(uid):
  e=entries[str(uid)];return raw[base+e['offset']:base+e['offset']+e['bytes']]
 def leaf(uid,count):
  assert entries[str(uid)]['name']=='mod_cc12_cct_data'
  data=blob(uid);assert len(data)==count*72,(uid,len(data),count)
  return [dict(trigger=[struct.unpack_from('<f',data,i*72+j*8)[0] for j in range(2)],
   matrix=list(struct.unpack_from('<9f',data,i*72+16)),offsets=list(struct.unpack_from('<3i',data,i*72+56))) for i in range(count)]
 def decode(uid,count,level=0):
  tag,trigger,child,fields=levels[level];assert entries[str(uid)]['name']==tag
  data=blob(uid);stride=(len(fields)+2)*8;assert len(data)==count*stride
  result=[]
  for start in range(0,len(data),stride):
   values=[struct.unpack_from('<Q' if level==2 else '<f',data,start+i*8)[0] for i in range(len(fields))]
   n,ref=struct.unpack_from('<QQ',data,start+len(fields)*8)
   result.append(dict(trigger=values,children=leaf(ref,n) if level==3 else decode(ref,n,level+1)))
  return result
 def xml_decode(parent,level=0):
  tag,trigger,child,fields=levels[level];result=[]
  for node in parent.findall(tag):
   values=[int(node.findtext(trigger))] if level==2 else [float(node.findtext(trigger+'/'+f)) for f in fields]
   if level==3:
    children=[dict(trigger=[float(n.findtext('cct_trigger/'+f)) for f in ['start','end']],
     matrix=[float(x) for x in n.findtext('cc12_rgn_data/c_tab/c').split()],
     offsets=[int(x) for x in n.findtext('cc12_rgn_data/k_tab/k').split()]) for n in node.findall(child+'/mod_cc12_cct_data')]
   else:children=xml_decode(node.find(child),level+1)
   result.append(dict(trigger=values,children=children))
  return result
 roots=[];analysis=bytearray(raw)
 for root in index['roots']:
  uid=root['uid'];data=blob(uid);words=root['words'];assert len(data)==144
  assert entries[str(words[17])]['name']==levels[0][0]
  roots.append(dict(uid=uid,enabled=words[0],control_method=[words[11],words[12]],
   led_sensitivity_trigger=[struct.unpack_from('<f',data,j*8)[0] for j in [13,14]],qfactor=words[15],core=decode(words[17],words[16])))
 table,count=struct.unpack_from('<II',raw,0x98);start,length=index['sections'][0][1:]
 for pos in range(start,start+length,72):
  uid=struct.unpack_from('<Q',raw,pos)[0]
  if entries[str(uid)]['name']!='cc12_ife':struct.pack_into('<I',analysis,pos+40,0)
 assert all(analysis[o:o+n]==raw[o:o+n] for _,o,n in index['sections'][1:])
 (P/(name+'-ccm-trees-private.json')).write_text(json.dumps(roots,indent=2)+'\n')
 work=Path('/home/cy122/x2pro-linux')/('parser-k333-'+name+'-ccm-r1');schema=work/'api/isp';dest=work/'xml'
 if not work.exists():
  work.mkdir(mode=0o700);schema.mkdir(parents=True);(work/'api/common').mkdir();dest.mkdir()
  for src,target in [(P/'sources/cc_1_2_0.xsd',schema/'cc_1_2_0.xsd'),
   (P.parent/'kernel298/ispglobalelements.xsd-reference-private',schema/'ispglobalelements.xsd'),
   (P.parent/'kernel298/globalelements.xsd-reference-private',work/'api/common/globalelements.xsd'),
   (P.parent/'kernel117/CamxChi/chi-cdk/api/chromatix/XSD/ParameterTuningTypes.xsd',schema/'ParameterTuningTypes.xsd')]:shutil.copyfile(src,target)
  (work/'analysis.bin').write_bytes(analysis)
  for item in [work,*work.rglob('*')]:os.chown(item,1000,1000)
 else:assert (work/'analysis.bin').read_bytes()==analysis
 exit_path=P/(name+'-parser-exit.json')
 if not exit_path.exists():
  reader=Path('/home/cy122/x2pro-linux/parser-k117')
  with (P/(name+'-parser.log')).open('xb') as log:
   q=subprocess.run(['stdbuf','-oL','-eL',str(reader/'ParameterParser'),str(dest),'x',str(schema),'-b'+str(work/'analysis.bin')],cwd=work,
    env=dict(os.environ,LD_LIBRARY_PATH=str(reader/'runtime/lib')),user=1000,group=1000,stdin=subprocess.DEVNULL,stdout=log,stderr=log,timeout=55)
  exit_path.write_text(json.dumps(dict(exit_code=q.returncode)));assert not q.returncode,(name,q.returncode)
 else:assert not json.loads(exit_path.read_text())['exit_code']
 records=[]
 for path in dest.rglob('cc12_ife.xml'):
  xml=ET.parse(path).getroot();core=xml_decode(xml.find('chromatix_cc12_core'))
  enabled=int(xml.findtext('enable_section/cc_enable'));qfactor=int(xml.findtext('chromatix_cc12_reserve/q_factor'))
  led=[float(xml.findtext('private_information/led_sensitivity_trigger/'+f)) for f in ['start','end']]
  matching=[r['uid'] for r in roots if norm(r['core'])==norm(core) and r['enabled']==enabled and r['qfactor']==qfactor and norm(r['led_sensitivity_trigger'])==norm(led)]
  assert matching,str(path)
  methods={c.tag:c.text for c in xml.find('control_method')}
  records.append(dict(selector=path.relative_to(dest).as_posix(),binary_uids=matching,all_matrices_offsets_and_triggers_match=True,control_method=methods,enabled=enabled,qfactor=qfactor))
 assert len(records)==len(roots) and {r['uid'] for r in roots}=={u for r in records for u in r['binary_uids']},(name,len(records),len(roots))
 def leaves(nodes):
  for node in nodes:
   if 'matrix' in node:yield node
   else:yield from leaves(node['children'])
 regions=[v for r in roots for v in leaves(r['core'])]
 assert all(all(math.isfinite(v) for v in r['matrix']) for r in regions)
 reports.append(dict(name=name,roots=len(roots),regions=len(regions),unique_profiles=len({json.dumps({k:v for k,v in r.items() if k!='uid'},sort_keys=True) for r in roots}),
  nonzero_offset_values=sum(v!=0 for r in regions for v in r['offsets']),selectors=records,full_tree_matches=True))
 print(json.dumps({k:v for k,v in reports[-1].items() if k!='selectors'}),flush=True)
report=dict(stage=333,sources=reports,all_factory_ccm_trees_verified=True,source_payload_and_mode_tree_unchanged=True,
 no_phone_operations=True,ccm_hardware_supported_by_deployed_backend=False,passed=True)
(HERE/'factory-ccm-validation.json').write_text(json.dumps(report,indent=2)+'\n');print('All retained IFE CCM matrices, offsets and complete trigger trees match OEM XML.')
