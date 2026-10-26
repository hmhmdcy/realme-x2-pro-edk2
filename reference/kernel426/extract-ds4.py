"""Recover target DS4 reserves and cross-check OEM XML and mode selection."""
from pathlib import Path
import importlib.util,json,os,shutil,struct,subprocess,sys,xml.etree.ElementTree as ET
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(s);s.loader.exec_module(storage)
WORK=storage.mounted_build().parent/'parser426';WORK.mkdir(mode=0o755,exist_ok=True)
sys.path.insert(0,str(HERE.parent/'kernel343'));from mode_tree import ModeTree
name=sys.argv[1] if len(sys.argv)>1 else 'sunny_s5kgw1'
inventory=json.loads((HERE.parent/'kernel349/downstream-gamma-inventory.json').read_text())
binding=next(v for v in inventory['sources'] if v['variant']==name)
index=json.loads((P.parent/'kernel333'/(name+'-index-private.json')).read_text());entries=index['entries']
path=P.parent/('kernel'+str(index['source_stage']))/index['filename'];raw=path.read_bytes();tree=ModeTree(path)
tags=['ds4to1v10_ife_full_dc4','ds4to1v10_ife_dc4_dc16','ds4to1v10_ife_disp_full_dc4','ds4to1v10_ife_disp_dc4_dc16']
roots=[]
for uid,e in entries.items():
 if e['name'] not in tags:continue
 data=raw[index['base']+e['offset']:index['base']+e['offset']+e['bytes']];assert len(data)==176
 passes=[list(struct.unpack_from('<4Q',data,48+32*i)) for i in range(4)]
 assert [r[0] for r in passes]==[0,1,2,3]
 assert all(all(v<=256 for v in r[1:]) and 256<=sum(r[1:])<=512 for r in passes)
 roots.append(dict(uid=int(uid),tag=e['name'],passes=passes))
assert len(roots)>=4
(P/(name+'-ds4-reserves-private.json')).write_text(json.dumps(roots,indent=2)+'\n')
analysis=bytearray(raw);start,length=next(s[1:] for s in index['sections'] if s[0]==0)
for pos in range(start,start+length,72):
 uid=struct.unpack_from('<Q',raw,pos)[0]
 if entries[str(uid)]['name'] not in tags:struct.pack_into('<I',analysis,pos+40,0)
assert all(analysis[o:o+n]==raw[o:o+n] for kind,o,n in index['sections'] if kind!=0)
work=WORK/name;directory=work/'api/isp';dest=work/'xml';directory.mkdir(parents=True,exist_ok=True);(work/'api/common').mkdir(exist_ok=True);dest.mkdir(exist_ok=True)
for source,target in [(P/'sources/ds4to1_1_0_0.xsd',directory/'ds4to1_1_0_0.xsd'),
 (P.parent/'kernel298/ispglobalelements.xsd-reference-private',directory/'ispglobalelements.xsd'),
 (P.parent/'kernel298/globalelements.xsd-reference-private',work/'api/common/globalelements.xsd'),
 (P.parent/'kernel117/CamxChi/chi-cdk/api/chromatix/XSD/ParameterTuningTypes.xsd',directory/'ParameterTuningTypes.xsd')]:shutil.copyfile(source,target)
(work/'analysis.bin').write_bytes(analysis);os.chmod(work,0o700)
for item in [work,*work.rglob('*')]:os.chown(item,1000,1000)
reader=Path('/home/cy122/x2pro-linux/parser-k117')
with (P/(name+'-ds4-parser.log')).open('wb') as stream:
 q=subprocess.run([str(reader/'ParameterParser'),str(dest),'x',str(directory),'-b'+str(work/'analysis.bin')],cwd=work,
  env=dict(os.environ,LD_LIBRARY_PATH=str(reader/'runtime/lib')),user=1000,group=1000,stdin=subprocess.DEVNULL,stdout=stream,stderr=stream,timeout=55)
assert not q.returncode,(name,q.returncode)
matched=[]
for tag in tags:
 for xp in dest.rglob(tag+'.xml'):
  xml=ET.parse(xp).getroot();rows=[]
  for node in xml.findall('chromatix_ds4to1v10_reserve/mod_ds4to1v10_pass_reserve_data'):
   trigger=['PASS_FULL','PASS_DC4','PASS_DC16','PASS_DC64'].index(node.findtext('pass_trigger'))
   rows.append([trigger,*[int(node.findtext('pass_data/'+field)) for field in ['coeff_07','coeff_16','coeff_25']]])
  ids=[r['uid'] for r in roots if r['tag']==tag and r['passes']==rows];assert ids,(tag,xp)
  matched.append(dict(selector=xp.relative_to(dest).as_posix(),uids=ids))
assert len(matched)==len(roots) and {r['uid'] for r in roots}=={u for row in matched for u in row['uids']}
queries=[];selected=[]
for item in binding['physical_contexts']:
 context=[0,item['sensor_mode_index'],0 if item['usecase']=='Preview' else 2,0,0,0,0]
 for tag in tags:
  found=tree.select(tag,context);assert found and any(r['uid']==found['uid'] and r['tag']==tag for r in roots)
  queries.append((tag,context,found));selected.append(dict(sensor_mode_index=item['sensor_mode_index'],usecase=item['usecase'],tag=tag,uid=found['uid'],mode_id=found['mode_id']))
q=subprocess.run([str(P.parent/'kernel343/stock-selection-manager'),str(path)],input=''.join(t+' '+' '.join(map(str,c))+'\n' for t,c,m in queries),text=True,capture_output=True,timeout=30)
assert not q.returncode and len(q.stdout.splitlines())==len(queries)
for i,((tag,context,found),line) in enumerate(zip(queries,q.stdout.splitlines())):assert line.split()==[str(i),tag,str(found['uid']),str(found['mode_id'])]
(P/(name+'-ds4-selection-private.json')).write_text(json.dumps(selected,indent=2)+'\n')
r=dict(stage=426,variant=name,roots=len(roots),passes_per_root=4,selected_physical_contexts=len(binding['physical_contexts']),mode_queries=len(queries),
 all_binary_reserves_match_oem_parser_xml=True,all_mode_queries_match_original_manager=True,all_coefficients_fit_schema=True,
 original_payload_and_mode_tree_unchanged=True,actual_runtime_pass_binding_not_yet_verified=True,coefficients_and_xml_private=True,phone_accessed=False,passed=True)
(HERE/(name+'-ds4-extraction-validation.json')).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
