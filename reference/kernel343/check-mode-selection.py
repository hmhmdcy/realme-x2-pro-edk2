"""Cross-check independent mode selection against the recovered stock manager."""
from pathlib import Path
import json,subprocess
import host
from mode_tree import ModeTree

HERE=Path(__file__).resolve().parent;P=host.PRIVATE
tags=['Metering','Arbitration','lsc34_ife','cc12_ife','MWBGainV1','refPtV1','sensorCalV1']
physical={'sunny_s5kgw1':[(2,[4608,3456]),(4,[4608,2592])],
 'sunny_imx471':[(1,[2304,1728])], 'sunny_imx319':[(0,[3264,2448]),(2,[1632,1224])],
 'qtech_s5k3m5sx':[(0,[4208,3120]),(3,[2104,1560])]}
reports=[];bindings={}
for name in ['qtech_s5kgw1',*physical]:
 index=json.loads((P.parent/'kernel333'/(name+'-index-private.json')).read_text());source=P.parent/('kernel'+str(index['source_stage']))/index['filename']
 tree=ModeTree(source);contexts=set()
 for uid in tree.nodes:
  values=[0]*7
  for kind,sub in tree.route(uid):values[kind]=sub
  contexts.add(tuple(values))
 for mode,_ in physical.get(name,[]):
  for usecase in [0,1,2]:contexts.add((0,mode,usecase,0,0,0,0))
 contexts=sorted(contexts);queries=[(tag,values) for values in contexts for tag in tags]
 text=''.join(tag+' '+' '.join(map(str,values))+'\n' for tag,values in queries)
 q=subprocess.run([str(P/'stock-selection-manager'),str(source)],input=text,capture_output=True,text=True,timeout=40)
 (P/(name+'-manager-results-private.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,q.stderr
 actual=q.stdout.splitlines();assert len(actual)==len(queries)
 for serial,((tag,values),line) in enumerate(zip(queries,actual)):
  fields=line.split();expected=tree.select(tag,values)
  assert fields==[str(serial),tag,str(expected['uid'] if expected else 0),str(expected['mode_id'] if expected else 0)],(name,values,tag,line,expected)
 rows=[]
 for mode,size in physical.get(name,[]):
  for usecase in [0,2]:
   values=[0,mode,usecase,0,0,0,0];selected={tag:tree.select(tag,values) for tag in tags}
   rows.append(dict(sensor_mode_index=mode,sensor_size=size,usecase='Preview' if usecase==0 else 'Video',context=values,selected=selected))
 bindings[name]=rows
 reports.append(dict(variant=name,mode_nodes=len(tree.nodes),module_descriptors=len(tree.modules),distinct_contexts=len(contexts),queries=len(queries),differences=0,
  actual_v11_no_link_format=True,complete_binary_mode_ids_used=True,physical_contexts=rows))
(P/'mode-bindings-private.json').write_text(json.dumps(bindings,indent=2)+'\n')
report=dict(stage=343,sources=reports,stock_generic_manager_compiled=True,stock_payload_parse_stubbed=True,
 independent_mode_tree_matches_stock=True,physical_geometry_evidence=['../kernel321/imx319-mode-mapping-validation.json','../kernel323/tele-mode-profile-validation.json','../kernel324/mode-profile-validation.json'],
 explicit_context_policy='original mode index + Preview/Video + no Feature1/Feature2/Scene/Effect',
 exact_target_hal_runtime_metadata_not_observed=True,front_upstream_crop_1928x1088_has_no_stock_mode_binding=True,phone_changed=False,passed=True)
(HERE/'mode-selection-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(queries=sum(r['queries'] for r in reports),variants=len(reports),differences=0,
 physical_modes=sum(len(v)//2 for v in bindings.values()),
 front_preview=next(r['selected'] for r in bindings['sunny_imx471'] if r['usecase']=='Preview')),indent=2))
