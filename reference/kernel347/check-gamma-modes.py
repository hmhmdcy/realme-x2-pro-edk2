"""Check the newly decoded Gamma tag against the existing original manager."""
from pathlib import Path
import json,struct,subprocess,sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
sys.path.insert(0,str(HERE.parent/'kernel343'))
from mode_tree import ModeTree
physical={'sunny_s5kgw1':[2,4],'sunny_imx471':[1],'sunny_imx319':[0,2],'qtech_s5k3m5sx':[0,3]}
reports=[];curves={}
def leaves(nodes):
 for n in nodes:
  if 'table' in n:yield n
  else:yield from leaves(n['children'])
for name in ['qtech_s5kgw1',*physical]:
 index=json.loads((P.parent/'kernel333'/(name+'-index-private.json')).read_text())
 source=P.parent/('kernel'+str(index['source_stage']))/index['filename'];tree=ModeTree(source)
 contexts=set()
 for uid in tree.nodes:
  values=[0]*7
  for kind,sub in tree.route(uid):values[kind]=sub
  contexts.add(tuple(values))
 for mode in physical.get(name,[]):
  for usecase in [0,2]:contexts.add((0,mode,usecase,0,0,0,0))
 contexts=sorted(contexts);query=''.join('gamma16_ife '+' '.join(map(str,v))+'\n' for v in contexts)
 q=subprocess.run([str(P.parent/'kernel343/stock-selection-manager'),str(source)],input=query,text=True,capture_output=True,timeout=35)
 assert not q.returncode,q.stderr;lines=q.stdout.splitlines();assert len(lines)==len(contexts)
 for serial,(values,line) in enumerate(zip(contexts,lines)):
  expected=tree.select('gamma16_ife',values)
  assert expected and line.split()==[str(serial),'gamma16_ife',str(expected['uid']),str(expected['mode_id'])]
 roots=json.loads((P/(name+'-gamma-trees-private.json')).read_text());by_uid={r['uid']:r for r in roots}
 rows=[]
 for mode in physical.get(name,[]):
  for usecase in [0,2]:
   selected=tree.select('gamma16_ife',[0,mode,usecase,0,0,0,0]);assert selected['uid'] in by_uid
   rows.append(dict(sensor_mode_index=mode,usecase='Preview' if usecase==0 else 'Video',gamma_uid=selected['uid'],enabled=by_uid[selected['uid']]['enabled']))
 values=[struct.pack('<65f',*v['table']) for r in roots for v in leaves(r['core'])]
 assert len(set(values))==1;curves[name]=values[0]
 reports.append(dict(variant=name,queries=len(contexts),differences=0,physical_contexts=rows,all_roots_share_one_curve=True))
report=dict(stage=347,sources=reports,queries=sum(r['queries'] for r in reports),
 original_generic_manager_reused_from343=True,all_five_variants_share_identical_curve=len(set(curves.values()))==1,
 static_gamma_sufficient_for_retained_ife_data=True,unknown_front_crop_not_bound=True,
 gamma_ipa_integrated=False,phone_changed=False,passed=True)
(HERE/'gamma-mode-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='sources'},indent=2))
