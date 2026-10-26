"""Inventory the original downstream Gamma stage before changing defaults."""
from pathlib import Path
import hashlib,importlib.util,json,struct,subprocess,sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
sys.path.insert(0,str(HERE.parent/'kernel343'));from mode_tree import ModeTree
schema_path='chi-cdk/api/chromatix/XSD/isp/gamma_1_5_0.xsd';commit='9f17f1b568626b393e785b369c5dc94543774d7a'
schema=P/'gamma_1_5_0-reference-private.xsd'
if not schema.exists():schema.write_bytes(subprocess.check_output(['git','-C','/home/cy122/x2pro-linux/refs/CamxChi-k117','show',commit+':'+schema_path]))
source=(HERE.parent/'kernel347/gamma-mode-validation.json');bindings=json.loads(source.read_text())['sources'];reports=[]
tags=['mod_gamma15_drc_gain_data','mod_gamma15_hdr_aec_data','mod_gamma15_led_idx_data','mod_gamma15_aec_data','mod_gamma15_cct_data','mod_gamma15_channel_data']
strides=[32,64,24,48,32,1040]
for binding in bindings:
 if not binding['physical_contexts']:continue
 name=binding['variant'];index=json.loads((P.parent/'kernel333'/(name+'-index-private.json')).read_text());entries=index['entries']
 path=P.parent/('kernel'+str(index['source_stage']))/index['filename'];raw=path.read_bytes();tree=ModeTree(path)
 def blob(uid):
  e=entries[str(uid)];return raw[index['base']+e['offset']:index['base']+e['offset']+e['bytes']]
 def visit(uid,count,level=0):
  assert entries[str(uid)]['name']==tags[level];data=blob(uid);stride=strides[level];assert len(data)==count*stride
  if level==5:return [(struct.unpack_from('<Q',data,i)[0],struct.unpack_from('<257f',data,i+8)) for i in range(0,len(data),stride)]
  result=[]
  for start in range(0,len(data),stride):
   n,ref=struct.unpack_from('<QQ',data,start+stride-16);result.extend(visit(ref,n,level+1))
  return result
 queries=[];selected=[]
 for item in binding['physical_contexts']:
  context=[0,item['sensor_mode_index'],0 if item['usecase']=='Preview' else 2,0,0,0,0]
  module=tree.select('gamma15_ipe',context);assert module
  words=struct.unpack('<17Q',blob(module['uid']));curves=visit(words[16],words[15]);assert all(c==3 for c,v in curves)
  nonlinear=sum(max(abs(value-(v[0]+(v[-1]-v[0])*i/256)) for i,value in enumerate(v))>1. for c,v in curves)
  selected.append(dict(sensor_mode_index=item['sensor_mode_index'],usecase=item['usecase'],uid=module['uid'],enabled=words[0],curves=len(curves),nonlinear_curves=nonlinear,
   independent_binary_traversal_only=True,xml_crosscheck_pending=True))
  queries.append((context,module))
 q=subprocess.run([str(P.parent/'kernel343/stock-selection-manager'),str(path)],input=''.join('gamma15_ipe '+' '.join(map(str,c))+'\n' for c,m in queries),text=True,capture_output=True,timeout=30)
 assert not q.returncode and len(q.stdout.splitlines())==len(queries)
 for i,((c,m),line) in enumerate(zip(queries,q.stdout.splitlines())):assert line.split()==[str(i),'gamma15_ipe',str(m['uid']),str(m['mode_id'])]
 reports.append(dict(variant=name,physical_contexts=selected))
report=dict(stage=349,schema=dict(path=schema_path,commit=commit,sha256=hashlib.sha256(schema.read_bytes()).hexdigest(),
 url='https://github.com/bjzhou/CamxChi/blob/'+commit+'/'+schema_path),sources=reports,
 actual_mode_queries=sum(len(r['physical_contexts']) for r in reports),original_manager_matches=True,
 downstream_gamma_stage_present=True,full_tree_and_pipeline_role_still_pending=True,
 not_yet_applied_to_vfe_or_default_profiles=True,phone_changed=False,passed=True)
(HERE/'downstream-gamma-inventory.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['schema','sources']},indent=2))
