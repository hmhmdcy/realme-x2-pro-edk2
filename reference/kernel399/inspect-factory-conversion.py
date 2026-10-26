"""Inspect only retained factory conversion modules and pinned schemas."""
from pathlib import Path
import importlib.util,json,subprocess,sys,hashlib
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(s);s.loader.exec_module(storage);source=storage.mounted_build().parent/'source354'
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()=='8b1e8903a550ffc20a2d8f1de574c37f2260fff3'
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'])
sys.path.insert(0,str(HERE.parent/'kernel343'));from mode_tree import ModeTree
names=['cst_1_2_0.xsd','cv_1_2_0.xsd'];out=P/'sources';out.mkdir(exist_ok=True);manifest=[]
for name in names:
 path='chi-cdk/api/chromatix/XSD/isp/'+name;target=out/name
 if not target.exists():target.write_bytes(subprocess.check_output(['git','-C','/home/cy122/x2pro-linux/refs/CamxChi-k117','show','9f17f1b568626b393e785b369c5dc94543774d7a:'+path],timeout=45))
 manifest.append(dict(path=path,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),bytes=target.stat().st_size,url='https://github.com/bjzhou/CamxChi/blob/9f17f1b568626b393e785b369c5dc94543774d7a/'+path))
rows=[]
for binding in json.loads((HERE.parent/'kernel349/downstream-gamma-inventory.json').read_text())['sources']:
 name=binding['variant'];idx=json.loads((P.parent/'kernel333'/(name+'-index-private.json')).read_text());raw=(P.parent/('kernel'+str(idx['source_stage']))/idx['filename']).read_bytes();tree=ModeTree(P.parent/('kernel'+str(idx['source_stage']))/idx['filename'])
 entries=idx['entries'];selected=[]
 for item in binding['physical_contexts']:
  context=[0,item['sensor_mode_index'],0 if item['usecase']=='Preview' else 2,0,0,0,0]
  modules={tag:tree.select(tag,context) for tag in ['cst12_ipe','cv12_ipe']}
  selected.append(dict(context=context,modules=modules))
 module_rows=[dict(uid=int(uid),name=e['name'],bytes=e['bytes']) for uid,e in entries.items() if e['name'] in ['cst12_ipe','cv12_ipe'] or e['name'].startswith('mod_cv12_')]
 (P/(name+'-conversion-inventory-private.json')).write_text(json.dumps(dict(entries=module_rows,selected=selected),indent=2)+'\n')
 rows.append(dict(variant=name,module_entries=len(module_rows),physical_contexts=len(selected),all_selected=all(all(v for v in s['modules'].values()) for s in selected),entry_shapes=sorted(set((r['name'],r['bytes']) for r in module_rows))))
(HERE/'primary-sources.json').write_text(json.dumps(dict(stage=399,commit='9f17f1b568626b393e785b369c5dc94543774d7a',files=manifest),indent=2)+'\n')
print(json.dumps(rows,indent=2))
