"""Decode all retained main/front IFE LSC trees and cross-check stock XML."""
from pathlib import Path
import json,math,os,shutil,struct,subprocess,xml.etree.ElementTree as ET
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
helpers=(HERE.parent/'kernel322/decode-trigger-tree.py').read_text();helpers=helpers[helpers.index('levels='):helpers.index('\nroots=[]')]
reports=[]
for name in ['qtech_s5kgw1','sunny_s5kgw1','sunny_imx471']:
 raw=(P/(name+'-tuning-private.bin')).read_bytes();table,count=struct.unpack_from('<II',raw,0x98)
 sections=[struct.unpack_from('<QQQ',raw,table+i*24) for i in range(count)]
 _,start,length=sections[0];base,size=sections[1][1:];assert start+length<=len(raw) and base+size<=len(raw);entries={}
 for pos in range(start,start+length,72):
  uid=struct.unpack_from('<Q',raw,pos)[0];tag=raw[pos+8:pos+40].split(b'\0')[0].decode();version,incr=struct.unpack_from('<II',raw,pos+40)
  offset,nbytes=struct.unpack_from('<QQ',raw,pos+56);assert offset+nbytes<=size
  entries[str(uid)]=dict(name=tag,version=version,increment=incr,offset=offset,bytes=nbytes)
 assert len(entries)==length//72
 ns=dict(entries=entries,raw=raw,base=base,channels=['r','gr','gb','b'],struct=struct,json=json);exec(helpers,ns)
 roots=[];selected=[];analysis=bytearray(raw)
 for pos in range(start,start+length,72):
  uid=struct.unpack_from('<Q',raw,pos)[0];entry=entries[str(uid)]
  if not entry['version']:continue
  if entry['name']!='lsc34_ife':struct.pack_into('<I',analysis,pos+40,0);continue
  selected.append(uid);words=struct.unpack_from('<'+'Q'*(entry['bytes']//8),raw,base+entry['offset'])
  refs=[dict(word=i,uid=v,name=entries[str(v)]['name']) for i,v in enumerate(words) if str(v) in entries]
  a=next(r for r in refs if r['name']=='mod_lsc34_lens_position_data');g=next(r for r in refs if r['name']=='mod_lsc34_golden_cct_data')
  roots.append(dict(uid=uid,core=ns['decode'](a['uid'],entries[str(a['uid'])]['bytes']//32),golden=ns['leaf'](g['uid'],entries[str(g['uid'])]['bytes']//3568)))
 def leaves(nodes):
  for n in nodes:
   if 'gains' in n:yield n
   else:yield from leaves(n['children'])
 all_leaves=[n for r in roots for n in leaves(r['core'])];all_golden=[n for r in roots for n in r['golden']]
 assert roots and all(len(v)==221 and all(math.isfinite(x) and x>0 for x in v) for n in all_leaves+all_golden for v in n['gains'].values())
 (P/(name+'-trees-private.json')).write_text(json.dumps(roots,indent=2)+'\n')
 work=Path('/home/cy122/x2pro-linux')/('parser-k324-'+name+'-lsc-r1');schema=work/'api/isp';dest=work/'xml'
 for _,offset,nbytes in sections[1:]:assert analysis[offset:offset+nbytes]==raw[offset:offset+nbytes]
 if not work.exists():
  work.mkdir(mode=0o700);schema.mkdir(parents=True);(work/'api/common').mkdir()
  for source,target in [(P.parent/'kernel317/sources/lsc_3_4_0.xsd',schema/'lsc_3_4_0.xsd'),
   (P.parent/'kernel298/ispglobalelements.xsd-reference-private',schema/'ispglobalelements.xsd'),
   (P.parent/'kernel298/globalelements.xsd-reference-private',work/'api/common/globalelements.xsd'),
   (P.parent/'kernel117/CamxChi/chi-cdk/api/chromatix/XSD/ParameterTuningTypes.xsd',schema/'ParameterTuningTypes.xsd')]:shutil.copyfile(source,target)
  (work/'analysis.bin').write_bytes(analysis);dest.mkdir()
  for p in [work,*work.rglob('*')]:os.chown(p,1000,1000)
  reader=Path('/home/cy122/x2pro-linux/parser-k117')
  with (P/(name+'-parser.log')).open('xb') as log:
   q=subprocess.run(['stdbuf','-oL','-eL',str(reader/'ParameterParser'),str(dest),'x',str(schema),'-b'+str(work/'analysis.bin')],cwd=work,
    env=dict(os.environ,LD_LIBRARY_PATH=str(reader/'runtime/lib')),user=1000,group=1000,stdin=subprocess.DEVNULL,stdout=log,stderr=log,timeout=55)
  (P/(name+'-parser-exit.json')).write_text(json.dumps(dict(exit_code=q.returncode)))
  assert not q.returncode
 else:
  assert (work/'analysis.bin').read_bytes()==analysis and json.loads((P/(name+'-parser-exit.json')).read_text())['exit_code']==0
 records=[];norm=ns['norm']
 for p in dest.rglob('lsc34_ife.xml'):
  tree=ET.parse(p);core=ns['xml_decode'](tree.find('chromatix_lsc34_core'));golden=[ns['xml_leaf'](n,True) for n in tree.findall('chromatix_lsc34_golden/mod_lsc34_golden_cct_data')]
  matches=[r['uid'] for r in roots if norm(r['core'])==norm(core) and norm(r['golden'])==norm(golden)];assert matches,str(p)
  records.append(dict(selector=p.relative_to(dest).as_posix(),binary_uids=matches,complete_trigger_tree_and_gains_match=True,
   control_method={c.tag:c.text for c in tree.find('control_method')},rolloff_enable=int(tree.findtext('enable_section/rolloff_enable'))))
 assert len(records)==len(selected) and {r['uid'] for r in roots}=={u for r in records for u in r['binary_uids']}
 reports.append(dict(name=name,ife_roots=len(roots),core_regions=len(all_leaves),golden_regions=len(all_golden),
  unique_complete_profiles=len({json.dumps(dict(core=r['core'],golden=r['golden']),sort_keys=True) for r in roots}),selectors=records,all_full_trees_match=True))
report=dict(stage=324,sources=reports,reused_complete_typed_decoder_stage=322,source_payload_and_mode_tree_unchanged=True,
 no_phone_operations=True,individual_values_applied=False,passed=True)
(HERE/'factory-lsc-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({**report,'sources':[{k:v for k,v in r.items() if k!='selectors'} for r in reports]},indent=2))
