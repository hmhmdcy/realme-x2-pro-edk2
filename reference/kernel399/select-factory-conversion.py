"""Bind CST/CV to retained physical contexts and verify the original manager."""
from pathlib import Path
import json,subprocess,sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'factory-conversion-validation.json').read_text())['passed']
sys.path.insert(0,str(HERE.parent/'kernel343'));from mode_tree import ModeTree
def leaves(nodes):
 for n in nodes:
  if 'children' in n:yield from leaves(n['children'])
  else:yield n
profiles={};rows=[];queries_count=0
for binding in json.loads((HERE.parent/'kernel349/downstream-gamma-inventory.json').read_text())['sources']:
 name=binding['variant'];idx=json.loads((P.parent/'kernel333'/(name+'-index-private.json')).read_text());path=P.parent/('kernel'+str(idx['source_stage']))/idx['filename'];tree=ModeTree(path);queries=[];profiles[name]=[]
 roots={tag:{r['uid']:r for r in json.loads((P/(name+'-'+tag+'-trees-private.json')).read_text())} for tag in ['cst12_ipe','cv12_ipe']}
 for item in binding['physical_contexts']:
  context=[0,item['sensor_mode_index'],0 if item['usecase']=='Preview' else 2,0,0,0,0];selected={}
  for tag in roots:
   module=tree.select(tag,context);assert module;queries.append((tag,context,module));selected[tag]=roots[tag][module['uid']]
  cst=selected['cst12_ipe'];cv=selected['cv12_ipe'];regions=list(leaves(cv['core']));reserve=cst['reserve']
  profiles[name].append(dict(sensor_mode_index=item['sensor_mode_index'],usecase=item['usecase'],modules=selected))
  rows.append(dict(variant=name,sensor_mode_index=item['sensor_mode_index'],usecase=item['usecase'],cst_root=cst['uid'],cv_root=cv['uid'],cst_enabled=cst['enabled'],cv_enabled=cv['enabled'],cv_regions=len(regions),cv_asymmetric_chroma_regions=sum(any(n['data'][p+'p']!=n['data'][p+'m'] for p in 'abcd') for n in regions),cst_nonidentity_matrix=reserve['m_tab']!=[1,0,0,0,1,0,0,0,1],cst_nonzero_subtract=any(reserve['s_tab']),cv_chroma_offsets_nonzero=any(n['data']['kcb'] or n['data']['kcr'] for n in regions)))
 q=subprocess.run([str(P.parent/'kernel343/stock-selection-manager'),str(path)],input=''.join(tag+' '+' '.join(map(str,c))+'\n' for tag,c,m in queries),text=True,capture_output=True,timeout=30)
 assert not q.returncode and len(q.stdout.splitlines())==len(queries)
 for i,((tag,c,m),line) in enumerate(zip(queries,q.stdout.splitlines())):assert line.split()==[str(i),tag,str(m['uid']),str(m['mode_id'])]
 queries_count+=len(queries)
(P/'mode-profiles-private.json').write_text(json.dumps(profiles,indent=2)+'\n')
report=dict(stage=399,physical_mode_contexts=len(rows),module_queries=queries_count,original_manager_matches=True,selected=rows,tuning_enable_not_equated_with_runtime_enable=True,no_factory_matrix_or_individual_values_public=True,phone_changed=False,passed=True)
(HERE/'mode-conversion-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
