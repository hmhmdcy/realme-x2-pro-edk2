"""Bind TMC10/TMC11 roots with the retained original mode selection manager."""
from pathlib import Path
import json,subprocess,sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
sys.path.insert(0,str(HERE.parent/'kernel343'));from mode_tree import ModeTree
inventory=json.loads((HERE.parent/'kernel349/downstream-gamma-inventory.json').read_text())
profiles={};rows=[];queries_count=0
for binding in inventory['sources']:
    name=binding['variant'];index=json.loads((P.parent/'kernel333'/(name+'-index-private.json')).read_text())
    path=P.parent/('kernel'+str(index['source_stage']))/index['filename'];tree=ModeTree(path)
    roots={tag:{r['uid']:r for r in json.loads((P.parent/stage/(name+suffix)).read_text())}
        for tag,stage,suffix in [('tmc10_sw','kernel410','-tmc10-trees-private.json'),('tmc11_sw','kernel412','-tmc11-trees-private.json')]}
    profiles[name]=[];queries=[]
    for item in binding['physical_contexts']:
        context=[0,item['sensor_mode_index'],0 if item['usecase']=='Preview' else 2,0,0,0,0];selected={}
        for tag in roots:
            module=tree.select(tag,context);assert module;queries.append((tag,context,module));selected[tag]=roots[tag][module['uid']]
        a,b=selected['tmc10_sw'],selected['tmc11_sw']
        rows.append(dict(variant=name,sensor_mode_index=item['sensor_mode_index'],usecase=item['usecase'],
            tmc10_root=a['uid'],tmc10_enabled=a['enabled'],tmc10_use_ltm=a['reserve']['use_ltm'],
            tmc11_root=b['uid'],tmc11_enabled=b['enabled'],tmc11_use_ltm=b['reserve']['use_ltm'],
            tmc11_curve_model=b['reserve']['curve_model'],tmc11_curve_order=b['reserve']['curve_order']))
        profiles[name].append(dict(sensor_mode_index=item['sensor_mode_index'],usecase=item['usecase'],modules=selected))
    q=subprocess.run([str(P.parent/'kernel343/stock-selection-manager'),str(path)],input=''.join(tag+' '+' '.join(map(str,c))+'\n' for tag,c,m in queries),text=True,capture_output=True,timeout=30)
    assert not q.returncode and len(q.stdout.splitlines())==len(queries)
    for i,((tag,context,module),line) in enumerate(zip(queries,q.stdout.splitlines())):
        assert line.split()==[str(i),tag,str(module['uid']),str(module['mode_id'])]
    queries_count+=len(queries)
(P/'mode-profiles-private.json').write_text(json.dumps(profiles,indent=2)+'\n')
result=dict(stage=412,physical_cameras=len(profiles),physical_mode_contexts=len(rows),module_queries=queries_count,
    original_manager_matches=True,ordinary_contexts_reused_from349=True,selected=rows,
    qtech_gw1_not_bound_to_an_extra_physical_camera=True,tuning_enable_not_equated_with_runtime_version=True,
    android_runtime_metadata_not_observed=True,phone_accessed=False,passed=True)
(HERE/'mode-tmc-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
