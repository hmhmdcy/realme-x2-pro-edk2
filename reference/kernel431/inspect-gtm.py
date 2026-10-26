"""Locate retained target GTM entry points and tuning roots for the next binding."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess,sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage431gtm',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.mounted_build()
old=P.parent/'kernel281';binary=old/'camera.qcom.so-private'
assert hashlib.sha256(binary.read_bytes()).hexdigest()=='e2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde'
symbols=(old/'hal-debug-symbols-with-size-private.txt').read_text();rows=[]
for name in ['IFEGTM10::Execute','IFEGTM10::RunCalculation','IFEGTM10::CheckDependenceChange','IFEGTM10::UpdateIFEInternalData','IQInterface::GTM10CalculateSetting','GTM10Interpolation::RunInterpolation','GTM10Setting::CalculateHWSetting']:
 candidates=[l for l in symbols.splitlines() if name+'(' in l]
 if not candidates:continue
 fields=candidates[0].split(maxsplit=3);start,size=int(fields[0],16),int(fields[1],16)
 raw=subprocess.check_output(['aarch64-linux-gnu-objdump','-d','--start-address='+hex(start),'--stop-address='+hex(start+size),str(binary)])
 (P/(name.replace('::','-')+'-private.asm')).write_bytes(raw);rows.append(dict(name=name,address=hex(start),bytes=size))
sys.path.insert(0,str(HERE.parent/'kernel343'));from mode_tree import ModeTree
inventory=json.loads((HERE.parent/'kernel349/downstream-gamma-inventory.json').read_text())
roots=[];queries_total=0
for variant in ['sunny_s5kgw1','sunny_imx471','qtech_s5k3m5sx','sunny_imx319']:
 index=json.loads((P.parent/'kernel333'/(variant+'-index-private.json')).read_text())
 entries=[dict(uid=uid,**v) for uid,v in index['entries'].items() if 'gtm' in v['name'].lower()]
 (P/(variant+'-gtm-directory-private.json')).write_text(json.dumps(entries,indent=2)+'\n')
 tree=ModeTree(P.parent/('kernel'+str(index['source_stage']))/index['filename'])
 binding=next(x for x in inventory['sources'] if x['variant']==variant);queries=[]
 for item in binding['physical_contexts']:
  context=[0,item['sensor_mode_index'],0 if item['usecase']=='Preview' else 2,0,0,0,0]
  found=tree.select('gtm10_ife',context);assert found and any(int(r['uid'])==found['uid'] and r['name']=='gtm10_ife' for r in entries)
  queries.append(('gtm10_ife',context,found))
 q=subprocess.run([str(P.parent/'kernel343/stock-selection-manager'),str(P.parent/('kernel'+str(index['source_stage']))/index['filename'])],input=''.join(t+' '+' '.join(map(str,c))+'\n' for t,c,m in queries),text=True,capture_output=True,timeout=30)
 assert not q.returncode and len(q.stdout.splitlines())==len(queries)
 for i,((tag,context,found),line) in enumerate(zip(queries,q.stdout.splitlines())):assert line.split()==[str(i),tag,str(found['uid']),str(found['mode_id'])]
 (P/(variant+'-gtm-selections-private.json')).write_text(json.dumps(queries,indent=2)+'\n');queries_total+=len(queries)
 roots.append(dict(variant=variant,directory_entries_including_subtrees=len(entries),module_roots=sum(e['name'] in ['gtm10_ife','gtm10_bps'] for e in entries),ife_mode_queries=len(queries),module_tags=sorted({e['name'] for e in entries})))
r=dict(stage=431,functions=rows,tuning_directory_inventory=roots,ordinary_ife_mode_queries=queries_total,all_queries_match_original_mode_manager=True,target_math_executed=False,gtm_register_application_or_history_association_complete=False,phone_accessed=False,passed=True)
(HERE/'gtm-location-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
