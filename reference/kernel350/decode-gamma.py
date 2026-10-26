"""Extract complete IPE Gamma trees and compare the retained OEM XML reader."""
from pathlib import Path
import json,math,os,shutil,struct,subprocess,xml.etree.ElementTree as ET
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
import importlib.util
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
WORK=storage.mounted_build().parent/'parser350';WORK.mkdir(mode=0o755,exist_ok=True)
levels=[('drc_gain','drc_gain_trigger','drc_gain_data',['start','end']),
 ('hdr_aec','hdr_aec_trigger','hdr_aec_data',['exp_time_start','exp_time_end','aec_sensitivity_start','aec_sensitivity_end','exp_gain_start','exp_gain_end']),
 ('led_idx','led_idx_trigger','led_idx_data',['led_index']),
 ('aec','aec_trigger','aec_data',['lux_idx_start','lux_idx_end','gain_start','gain_end']),
 ('cct','cct_trigger','cct_data',['start','end'])]
def norm(v):
 if isinstance(v,float):return float(format(v,'.6g'))
 if isinstance(v,list):return [norm(x) for x in v]
 if isinstance(v,dict):return {k:norm(x) for k,x in v.items()}
 return v
reports=[]
for name in ['qtech_s5kgw1','sunny_s5kgw1','sunny_imx471','qtech_s5k3m5sx','sunny_imx319']:
 index=json.loads((P.parent/'kernel333'/(name+'-index-private.json')).read_text());entries=index['entries'];base=index['base']
 source=P.parent/('kernel'+str(index['source_stage']))/index['filename'];raw=source.read_bytes()
 def blob(uid):
  e=entries[str(uid)];return raw[base+e['offset']:base+e['offset']+e['bytes']]
 def channels(uid,count):
  assert entries[str(uid)]['name']=='mod_gamma15_channel_data'
  data=blob(uid);assert len(data)==count*1040,(uid,count,len(data))
  result=[]
  for start in range(0,len(data),1040):
   result.append(dict(channel=struct.unpack_from('<Q',data,start)[0],table=list(struct.unpack_from('<257f',data,start+8))))
  return result
 def decode(uid,count,level=0):
  tag,trigger,child,fields=levels[level];assert entries[str(uid)]['name']=='mod_gamma15_'+tag+'_data'
  data=blob(uid);stride=(len(fields)+2)*8;assert len(data)==count*stride,(uid,len(data),count,stride)
  result=[]
  for start in range(0,len(data),stride):
   values=[struct.unpack_from('<Q' if level==2 else '<f',data,start+i*8)[0] for i in range(len(fields))]
   n,ref=struct.unpack_from('<QQ',data,start+len(fields)*8)
   result.append(dict(trigger=values,children=channels(ref,n) if level==4 else decode(ref,n,level+1)))
  return result
 channel_ids={'channel_G':0,'channel_B':1,'channel_R':2,'channel_RGB':3}
 def xml_decode(parent,level=0):
  tag,trigger,child,fields=levels[level];result=[]
  for node in parent.findall('mod_gamma15_'+tag+'_data'):
   values=[int(node.findtext(trigger))] if level==2 else [float(node.findtext(trigger+'/'+f)) for f in fields]
   if level==4:
    children=[dict(channel=channel_ids[n.findtext('channel_type')],table=[float(x) for x in n.findtext('gamma15_rgn_data/table').split()]) for n in node.findall(child+'/mod_gamma15_channel_data')]
   else:children=xml_decode(node.find(child),level+1)
   result.append(dict(trigger=values,children=children))
  return result
 roots=[];analysis=bytearray(raw)
 for uid,e in entries.items():
  if e['name']!='gamma15_ipe':continue
  data=blob(int(uid));assert len(data)==136
  words=struct.unpack('<17Q',data)
  roots.append(dict(uid=int(uid),enabled=words[0],control_method=[words[11],words[12]],
   led_sensitivity_trigger=[struct.unpack_from('<f',data,j*8)[0] for j in [13,14]],core=decode(words[16],words[15])))
 start,length=next(s[1:] for s in index['sections'] if s[0]==0)
 for pos in range(start,start+length,72):
  uid=struct.unpack_from('<Q',raw,pos)[0]
  if entries[str(uid)]['name']!='gamma15_ipe':struct.pack_into('<I',analysis,pos+40,0)
 assert all(analysis[o:o+n]==raw[o:o+n] for kind,o,n in index['sections'] if kind!=0)
 (P/(name+'-gamma-trees-private.json')).write_text(json.dumps(roots,indent=2)+'\n')
 work=WORK/(name+'-gamma-r1');schema=work/'api/isp';dest=work/'xml'
 if not work.exists():
  work.mkdir(mode=0o700);schema.mkdir(parents=True);(work/'api/common').mkdir();dest.mkdir()
  for src,target in [(P/'sources/gamma_1_5_0.xsd',schema/'gamma_1_5_0.xsd'),
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
 for path in dest.rglob('gamma15_ipe.xml'):
  xml=ET.parse(path).getroot();core=xml_decode(xml.find('chromatix_gamma15_core'));enabled=int(xml.findtext('enable_section/gamma_enable'))
  led=[float(xml.findtext('private_information/led_sensitivity_trigger/'+f)) for f in ['start','end']]
  methods={c.tag:c.text for c in xml.find('control_method')}
  control=[['control_lux_idx','control_gain'].index(methods['aec_exp_control']),
   ['control_exp_time_ratio','control_aec_exp_sensitivity_ratio','control_exp_gain_ratio'].index(methods['aec_hdr_control'])]
  matching=[r['uid'] for r in roots if norm(r['core'])==norm(core) and r['enabled']==enabled and norm(r['led_sensitivity_trigger'])==norm(led) and r['control_method']==control]
  assert matching,str(path)
  records.append(dict(selector=path.relative_to(dest).as_posix(),binary_uids=matching,full_curves_and_triggers_match=True,control_method=methods,enabled=enabled))
 assert len(records)==len(roots) and {r['uid'] for r in roots}=={u for r in records for u in r['binary_uids']},(name,len(records),len(roots))
 def leaves(nodes):
  for node in nodes:
   if 'table' in node:yield node
   else:yield from leaves(node['children'])
 curves=[v for r in roots for v in leaves(r['core'])];assert all(math.isfinite(v) for c in curves for v in c['table'])
 reports.append(dict(variant=name,roots=len(roots),channel_curves=len(curves),samples_per_curve=257,
  unique_channel_curves=len({struct.pack('<257f',*c['table']) for c in curves}),
  non_monotonic_curves=sum(any(a>b for a,b in zip(c['table'],c['table'][1:])) for c in curves),
  channel_types=sorted({c['channel'] for c in curves}),selectors=records,full_tree_matches=True))
 print(json.dumps({k:v for k,v in reports[-1].items() if k!='selectors'}),flush=True)
report=dict(stage=350,sources=reports,all_retained_ipe_gamma_trees_verified=True,
 source_payload_and_mode_tree_unchanged=True,all_curves_private=True,phone_changed=False,gamma_ipa_integrated=False,passed=True)
(HERE/'factory-gamma-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('Extracted factory Gamma curves and full trigger trees; all match retained OEM XML.',flush=True)
