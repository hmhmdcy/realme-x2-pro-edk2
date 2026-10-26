"""Cross-check telephoto triggers and meshes with the retained stock data parser."""
from pathlib import Path
import importlib.util,json,os,shutil,struct,subprocess,sys,xml.etree.ElementTree as ET
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
raw=(P.parent/'kernel306/qtech-s5k3m5sx-tuning-private.bin').read_bytes()
work=Path('/home/cy122/x2pro-linux/parser-k323-tele-lsc-r1')
schema=work/'api/isp';dest=work/'xml'
table,count=struct.unpack_from('<II',raw,0x98);sections=[struct.unpack_from('<QQQ',raw,table+i*24) for i in range(count)]
_,start,length=sections[0];analysis=bytearray(raw);selected=[]
for pos in range(start,start+length,72):
 uid=struct.unpack_from('<Q',raw,pos)[0];name=raw[pos+8:pos+40].split(b'\0')[0].decode();version=struct.unpack_from('<I',raw,pos+40)[0]
 if not version:continue
 if name=='lsc34_ife':selected.append(uid)
 else:struct.pack_into('<I',analysis,pos+40,0)
assert selected
for _,offset,size in sections[1:]:assert analysis[offset:offset+size]==raw[offset:offset+size]
if '--collect' not in sys.argv:
 assert not work.exists();work.mkdir(mode=0o700)
 schema.mkdir(parents=True);(work/'api/common').mkdir()
 for source,target in [(P.parent/'kernel317/sources/lsc_3_4_0.xsd',schema/'lsc_3_4_0.xsd'),
  (P.parent/'kernel298/ispglobalelements.xsd-reference-private',schema/'ispglobalelements.xsd'),
  (P.parent/'kernel298/globalelements.xsd-reference-private',work/'api/common/globalelements.xsd'),
  (P.parent/'kernel117/CamxChi/chi-cdk/api/chromatix/XSD/ParameterTuningTypes.xsd',schema/'ParameterTuningTypes.xsd')]:shutil.copyfile(source,target)
 (work/'analysis.bin').write_bytes(analysis);dest.mkdir()
 for p in [work,*work.rglob('*')]:os.chown(p,1000,1000)
 reader=Path('/home/cy122/x2pro-linux/parser-k117')
 with (P/'tele-parser.log').open('xb') as log:
  q=subprocess.run(['stdbuf','-oL','-eL',str(reader/'ParameterParser'),str(dest),'x',str(schema),'-b'+str(work/'analysis.bin')],cwd=work,
   env=dict(os.environ,LD_LIBRARY_PATH=str(reader/'runtime/lib')),user=1000,group=1000,stdin=subprocess.DEVNULL,stdout=log,stderr=log,timeout=55)
 assert not q.returncode
else:
 assert (work/'analysis.bin').read_bytes()==analysis
text=(HERE.parent/'kernel322/decode-trigger-tree.py').read_text();ns={'struct':struct,'json':json,'channels':['r','gr','gb','b']}
exec(text[text.index('levels='):text.index('\nroots=[]')],ns)
roots=json.loads((P/'tele-trigger-trees-private.json').read_text());records=[]
norm=ns['norm']
for p in dest.rglob('lsc34_ife.xml'):
 tree=ET.parse(p);core=ns['xml_decode'](tree.find('chromatix_lsc34_core'));golden=[ns['xml_leaf'](n,True) for n in tree.findall('chromatix_lsc34_golden/mod_lsc34_golden_cct_data')]
 matches=[r['uid'] for r in roots if norm(r['core'])==norm(core) and norm(r['golden'])==norm(golden)]
 assert matches,str(p)
 records.append(dict(selector=p.relative_to(dest).as_posix(),binary_uids=matches,complete_trigger_tree_and_gains_match=True,
  control_method={c.tag:c.text for c in tree.find('control_method')},rolloff_enable=int(tree.findtext('enable_section/rolloff_enable'))))
assert len(records)==len(selected) and {r['uid'] for r in roots}=={u for r in records for u in r['binary_uids']}
report=dict(stage=323,sensor='s5k3m5',selected_roots=len(selected),selectors=records,all_full_trees_match=True,
 original_reader_exit=0,source_payload_and_mode_tree_unchanged=True,no_phone_operations=True,passed=True)
(HERE/'tele-trigger-tree-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(stage=323,roots=len(selected),all_full_trees_match=True,passed=True),indent=2))
