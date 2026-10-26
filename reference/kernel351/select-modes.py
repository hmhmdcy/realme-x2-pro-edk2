"""Bind the newly decoded modules using the existing physical mode contexts."""
from pathlib import Path
import json,subprocess,sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
sys.path.insert(0,str(HERE.parent/'kernel343'));from mode_tree import ModeTree
profiles={};rows=[];queries_count=0
for binding in json.loads((HERE.parent/'kernel349/downstream-gamma-inventory.json').read_text())['sources']:
 name=binding['variant'];idx=json.loads((P.parent/'kernel333'/(name+'-index-private.json')).read_text())
 path=P.parent/('kernel'+str(idx['source_stage']))/idx['filename'];tree=ModeTree(path);queries=[];profiles[name]=[]
 roots={tag:{r['uid']:r for r in json.loads((P/(name+'-'+tag+'-trees-private.json')).read_text())} for tag in ['ltm13_ipe','cc13_ipe']}
 for item in binding['physical_contexts']:
  context=[0,item['sensor_mode_index'],0 if item['usecase']=='Preview' else 2,0,0,0,0];selected={}
  for tag in roots:
   module=tree.select(tag,context);assert module;queries.append((tag,context,module));selected[tag]=roots[tag][module['uid']]
  ltm=selected['ltm13_ipe'];ccm=selected['cc13_ipe']
  rows.append(dict(variant=name,sensor_mode_index=item['sensor_mode_index'],usecase=item['usecase'],
   ltm_root=ltm['uid'],ltm_module_enabled=ltm['enabled'],ltm_enabled=ltm['reserve']['ltm_en'],
   inverse_gamma_enabled=ltm['reserve']['igamma_en'],data_collection_enabled=ltm['reserve']['data_collect_en'],
   image_processing_enabled=ltm['reserve']['img_process_en'],ccm_root=ccm['uid'],ccm_enabled=ccm['enabled'],ccm_qfactor=ccm['qfactor']))
  profiles[name].append(dict(sensor_mode_index=item['sensor_mode_index'],usecase=item['usecase'],modules=selected))
 q=subprocess.run([str(P.parent/'kernel343/stock-selection-manager'),str(path)],input=''.join(tag+' '+' '.join(map(str,c))+'\n' for tag,c,m in queries),text=True,capture_output=True,timeout=30)
 assert not q.returncode and len(q.stdout.splitlines())==len(queries)
 for i,((tag,c,m),line) in enumerate(zip(queries,q.stdout.splitlines())):assert line.split()==[str(i),tag,str(m['uid']),str(m['mode_id'])]
 queries_count+=len(queries)
(P/'mode-profiles-private.json').write_text(json.dumps(profiles,indent=2)+'\n')
report=dict(stage=351,physical_mode_contexts=len(rows),module_queries=queries_count,original_manager_matches=True,
 mode_contexts_reused_from349=True,selected=rows,tuning_enable_not_equated_with_android_runtime_enable=True,
 phone_changed=False,passed=True)
(HERE/'mode-colour-chain-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
