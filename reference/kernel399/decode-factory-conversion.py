"""Decode complete retained IPE CST/CV roots and compare the stock XML reader."""
from pathlib import Path
import hashlib,importlib.util,json,os,shutil,struct,subprocess,xml.etree.ElementTree as ET
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(s);s.loader.exec_module(storage)
WORK=storage.mounted_build().parent/'parser399';WORK.mkdir(mode=0o755,exist_ok=True)
NS={'x':'http://www.w3.org/2001/XMLSchema'}
def layout(file,typename):
 root=ET.parse(P/'sources'/file);result=[];offset=0
 for e in root.findall('x:complexType[@name="'+typename+'"]/x:sequence/x:element',NS):
  attrs={a.attrib['name']:a.attrib.get('fixed',a.attrib.get('default')) for a in e.findall('.//x:attribute',NS)}
  count=int(attrs['length']);fmt={'float':'f','int':'i','uint':'I'}[attrs.get('tool_hint',attrs['type'])];child=e.find('x:complexType/x:sequence/x:element',NS)
  result.append(dict(name=e.attrib['name'],count=count,format=fmt,offset=offset,child=child.attrib['name'] if child is not None else None));offset+=(count*4+7)//8*8
 return result,offset
cst_fields,cst_size=layout('cst_1_2_0.xsd','chromatix_cst12_reserveType');cv_fields,cv_size=layout('cv_1_2_0.xsd','cv12_rgn_dataType');assert(cst_size,cv_size)==(104,112)
def readfields(raw,start,fields):
 out={}
 for f in fields:
  values=list(struct.unpack_from('<'+str(f['count'])+f['format'],raw,start+f['offset']));out[f['name']]=values if f['count']>1 else values[0]
 return out
def xmlfields(node,fields):
 out={}
 for f in fields:
  text=node.findtext(f['name']+('/'+f['child'] if f['child'] else ''));assert text is not None,f
  values=[(float if f['format']=='f' else int)(n) for n in text.split()];assert len(values)==f['count'];out[f['name']]=values if f['count']>1 else values[0]
 return out
def norm(v):
 if isinstance(v,float):return float(format(v,'.6g'))
 if isinstance(v,list):return [norm(n) for n in v]
 if isinstance(v,dict):return {k:norm(n) for k,n in v.items()}
 return v
axes=[('drc_gain','drc_gain_trigger','drc_gain_data',['start','end']),('hdr_aec','hdr_aec_trigger','hdr_aec_data',['exp_time_start','exp_time_end','aec_sensitivity_start','aec_sensitivity_end','exp_gain_start','exp_gain_end']),('led','led_trigger','led_data',['led_index']),('aec','aec_trigger','aec_data',['lux_idx_start','lux_idx_end','gain_start','gain_end'])]
def xml_cv(parent,level=0):
 tag,trig,child,fields=axes[level];out=[]
 for node in parent.findall('mod_cv12_'+tag+'_data'):
  values=[int(node.findtext(trig))] if level==2 else [float(node.findtext(trig+'/'+f)) for f in fields]
  children=[dict(trigger=[float(n.findtext('cct_trigger/'+f)) for f in ['start','end']],data=xmlfields(n.find('cv12_rgn_data'),cv_fields)) for n in node.findall(child+'/mod_cv12_cct_data')] if level==3 else xml_cv(node.find(child),level+1)
  out.append(dict(trigger=values,children=children))
 return out
reports=[]
for name in ['qtech_s5kgw1','sunny_s5kgw1','sunny_imx471','qtech_s5k3m5sx','sunny_imx319']:
 idx=json.loads((P.parent/'kernel333'/(name+'-index-private.json')).read_text());entries=idx['entries'];raw=(P.parent/('kernel'+str(idx['source_stage']))/idx['filename']).read_bytes()
 def blob(uid):
  e=entries[str(uid)];return raw[idx['base']+e['offset']:idx['base']+e['offset']+e['bytes']]
 def cv_leaf(uid,count):
  assert entries[str(uid)]['name']=='mod_cv12_cct_data';data=blob(uid);assert len(data)==count*128
  return [dict(trigger=[struct.unpack_from('<f',data,i+j*8)[0] for j in range(2)],data=readfields(data,i+16,cv_fields)) for i in range(0,len(data),128)]
 def cv(uid,count,level=0):
  tag,trig,child,fields=axes[level];assert entries[str(uid)]['name']=='mod_cv12_'+tag+'_data';data=blob(uid);stride=(len(fields)+2)*8;assert len(data)==count*stride;out=[]
  for offset in range(0,len(data),stride):
   values=[struct.unpack_from('<Q' if level==2 else '<f',data,offset+j*8)[0] for j in range(len(fields))];n,ref=struct.unpack_from('<QQ',data,offset+len(fields)*8)
   out.append(dict(trigger=values,children=cv_leaf(ref,n) if level==3 else cv(ref,n,level+1)))
  return out
 roots={'cst12_ipe':[],'cv12_ipe':[]};analysis=bytearray(raw)
 for uid,e in entries.items():
  if e['name'] not in roots:continue
  data=blob(int(uid));words=struct.unpack('<'+str(len(data)//8)+'Q',data)
  if e['name']=='cst12_ipe':assert len(data)==152;row=dict(uid=int(uid),enabled=words[0],reserve=readfields(data,48,cst_fields))
  else:
   assert len(data)==136;row=dict(uid=int(uid),enabled=words[0],control_method=[words[11],words[12]],led_sensitivity_trigger=[struct.unpack_from('<f',data,i*8)[0] for i in [13,14]],core=cv(words[16],words[15]))
  roots[e['name']].append(row)
 for tag,rows in roots.items():(P/(name+'-'+tag+'-trees-private.json')).write_text(json.dumps(rows,indent=2)+'\n')
 start,length=next(s[1:] for s in idx['sections'] if s[0]==0)
 for pos in range(start,start+length,72):
  uid=struct.unpack_from('<Q',raw,pos)[0]
  if entries[str(uid)]['name'] not in roots:struct.pack_into('<I',analysis,pos+40,0)
 assert all(analysis[o:o+n]==raw[o:o+n] for kind,o,n in idx['sections'] if kind!=0)
 work=WORK/(name+'-conversion-r1');directory=work/'api/isp';dest=work/'xml'
 if not work.exists():
  directory.mkdir(parents=True);(work/'api/common').mkdir();dest.mkdir();os.chmod(work,0o700)
  for source,target in [(P/'sources/cst_1_2_0.xsd',directory/'cst_1_2_0.xsd'),(P/'sources/cv_1_2_0.xsd',directory/'cv_1_2_0.xsd'),(P.parent/'kernel298/ispglobalelements.xsd-reference-private',directory/'ispglobalelements.xsd'),(P.parent/'kernel298/globalelements.xsd-reference-private',work/'api/common/globalelements.xsd'),(P.parent/'kernel117/CamxChi/chi-cdk/api/chromatix/XSD/ParameterTuningTypes.xsd',directory/'ParameterTuningTypes.xsd')]:shutil.copyfile(source,target)
  (work/'analysis.bin').write_bytes(analysis)
  for item in [work,*work.rglob('*')]:os.chown(item,1000,1000)
 else:assert (work/'analysis.bin').read_bytes()==analysis
 exitpath=P/(name+'-parser-exit.json')
 if not exitpath.exists():
  reader=Path('/home/cy122/x2pro-linux/parser-k117')
  with (P/(name+'-parser.log')).open('xb') as log:
   q=subprocess.run([str(reader/'ParameterParser'),str(dest),'x',str(directory),'-b'+str(work/'analysis.bin')],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=str(reader/'runtime/lib')),user=1000,group=1000,stdin=subprocess.DEVNULL,stdout=log,stderr=log,timeout=55)
  exitpath.write_text(json.dumps(dict(exit_code=q.returncode)));assert not q.returncode,(name,q.returncode)
 else:assert not json.loads(exitpath.read_text())['exit_code']
 for tag,rows in roots.items():
  matches=[]
  for path in dest.rglob(tag+'.xml'):
   xml=ET.parse(path).getroot();is_cst=tag=='cst12_ipe';row=dict(enabled=int(xml.findtext('enable_section/'+('cst_enable' if is_cst else 'cv_enable'))))
   if is_cst:row['reserve']=xmlfields(xml.find('chromatix_cst12_reserve'),cst_fields)
   else:
    methods={c.tag:c.text for c in xml.find('control_method')};row.update(control_method=[['control_lux_idx','control_gain'].index(methods['aec_exp_control']),['control_exp_time_ratio','control_aec_exp_sensitivity_ratio','control_exp_gain_ratio'].index(methods['aec_hdr_control'])],led_sensitivity_trigger=[float(xml.findtext('private_information/led_sensitivity_trigger/'+f)) for f in ['start','end']],core=xml_cv(xml.find('chromatix_cv12_core')))
   ids=[r['uid'] for r in rows if norm({k:v for k,v in r.items() if k!='uid'})==norm(row)]
   if not ids:(P/(name+'-'+tag+'-unmatched-private.json')).write_text(json.dumps(row,indent=2)+'\n');raise AssertionError((name,tag,str(path)))
   matches.append(dict(selector=path.relative_to(dest).as_posix(),uids=ids))
  assert len(matches)==len(rows) and {r['uid'] for r in rows}=={i for m in matches for i in m['uids']}
  (P/(name+'-'+tag+'-xml-matches-private.json')).write_text(json.dumps(matches,indent=2)+'\n')
  def leaves(nodes):
   for n in nodes:
    if 'children' in n:yield from leaves(n['children'])
    else:yield n
  reports.append(dict(variant=name,module=tag,roots=len(rows),regions=0 if tag=='cst12_ipe' else sum(len(list(leaves(r['core']))) for r in rows),complete_tree_and_reserve_xml_match=True))
  print(json.dumps(reports[-1]),flush=True)
(HERE/'factory-conversion-validation.json').write_text(json.dumps(dict(stage=399,sources=reports,original_factory_payloads_unchanged=True,only_analysis_module_table_enable_flags_changed=True,original_reader_xml_crosscheck=True,phone_changed=False,all_tables_private=True,passed=True),indent=2)+'\n')
