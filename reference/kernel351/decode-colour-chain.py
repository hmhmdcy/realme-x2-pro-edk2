"""Extract IPE LTM/CCM trees and compare a retained OEM XML reader."""
from pathlib import Path
import hashlib,importlib.util,json,math,os,shutil,struct,subprocess,sys,xml.etree.ElementTree as ET
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
WORK=storage.mounted_build().parent/'parser351';WORK.mkdir(mode=0o755,exist_ok=True)
NS={'x':'http://www.w3.org/2001/XMLSchema'}
schema=ET.parse(P/'sources/ltm_1_3_0.xsd')
def fields(type_name):
 out=[];offset=0
 for e in schema.findall('x:complexType[@name="'+type_name+'"]/x:sequence/x:element',NS):
  attributes={a.attrib['name']:a.attrib.get('fixed',a.attrib.get('default')) for a in e.findall('.//x:attribute',NS)}
  count=int(attributes['length']);kind=attributes.get('tool_hint',attributes['type']);fmt={'float':'f','uint':'I','int':'i'}[kind]
  name=e.attrib['name'];child=None
  if count>1:child=e.find('x:complexType/x:sequence/x:element',NS).attrib['name']
  out.append(dict(name=name,child=child,count=count,format=fmt,offset=offset));offset+=(4*count+7)//8*8
 return out,offset
reserve_fields,reserve_size=fields('chromatix_ltm13_reserveType');region_fields,region_size=fields('ltm13_rgn_dataType')
assert reserve_size==768
def read_fields(data,offset,layout):
 out={}
 for f in layout:
  values=list(struct.unpack_from('<'+str(f['count'])+f['format'],data,offset+f['offset']))
  out[f['name']]=values if f['count']>1 else values[0]
 return out
def xml_fields(node,layout):
 out={}
 for f in layout:
  path=f['name']+('/'+f['child'] if f['child'] else '')
  values=[(float if f['format']=='f' else int)(s) for s in node.findtext(path).split()]
  assert len(values)==f['count'];out[f['name']]=values if f['count']>1 else values[0]
 return out
def norm(v):
 if isinstance(v,float):return float(format(v,'.6g'))
 if isinstance(v,list):return [norm(x) for x in v]
 if isinstance(v,dict):return {k:norm(x) for k,x in v.items()}
 return v
def methods(xml):
 d={c.tag:c.text for c in xml.find('control_method')}
 return [['control_lux_idx','control_gain'].index(d['aec_exp_control']),['control_exp_time_ratio','control_aec_exp_sensitivity_ratio','control_exp_gain_ratio'].index(d['aec_hdr_control'])]
axes=[('drc_gain','drc_gain_trigger','drc_gain_data',['start','end']),('hdr_aec','hdr_aec_trigger','hdr_aec_data',['exp_time_start','exp_time_end','aec_sensitivity_start','aec_sensitivity_end','exp_gain_start','exp_gain_end']),('led_idx','led_idx_trigger','led_idx_data',['led_index']),('aec','aec_trigger','aec_data',['lux_idx_start','lux_idx_end','gain_start','gain_end'])]
reports=[]
for name in ['qtech_s5kgw1','sunny_s5kgw1','sunny_imx471','qtech_s5k3m5sx','sunny_imx319']:
 idx=json.loads((P.parent/'kernel333'/(name+'-index-private.json')).read_text());entries=idx['entries']
 raw=(P.parent/('kernel'+str(idx['source_stage']))/idx['filename']).read_bytes()
 def blob(uid):
  e=entries[str(uid)];return raw[idx['base']+e['offset']:idx['base']+e['offset']+e['bytes']]
 def ccm_leaf(uid,count):
  assert entries[str(uid)]['name']=='mod_cc13_cct_data';data=blob(uid);assert len(data)==count*72
  return [dict(trigger=[struct.unpack_from('<f',data,i+j*8)[0] for j in range(2)],matrix=list(struct.unpack_from('<9f',data,i+16)),offsets=list(struct.unpack_from('<3i',data,i+56))) for i in range(0,len(data),72)]
 def ccm(uid,count,level=0):
  tag,trig,child,fs=axes[level];assert entries[str(uid)]['name']=='mod_cc13_'+tag+'_data'
  data=blob(uid);stride=(len(fs)+2)*8;assert len(data)==count*stride;result=[]
  for offset in range(0,len(data),stride):
   values=[struct.unpack_from('<Q' if level==2 else '<f',data,offset+j*8)[0] for j in range(len(fs))]
   n,ref=struct.unpack_from('<QQ',data,offset+len(fs)*8)
   result.append(dict(trigger=values,children=ccm_leaf(ref,n) if level==3 else ccm(ref,n,level+1)))
  return result
 def ltm(uid,count,level=0):
  tag,trig,child,fs=axes[[0,1,3][level]];assert entries[str(uid)]['name']=='mod_ltm13_'+tag+'_data'
  data=blob(uid);stride=(len(fs)+2)*8 if level<2 else len(fs)*8+region_size
  assert len(data)==count*stride,(name,uid,count,len(data),stride);result=[]
  for offset in range(0,len(data),stride):
   row=dict(trigger=[struct.unpack_from('<f',data,offset+j*8)[0] for j in range(len(fs))])
   if level<2:
    n,ref=struct.unpack_from('<QQ',data,offset+len(fs)*8);row['children']=ltm(ref,n,level+1)
   else:row['data']=read_fields(data,offset+len(fs)*8,region_fields)
   result.append(row)
  return result
 def xml_ccm(parent,level=0):
  tag,trig,child,fs=axes[level];out=[]
  for node in parent.findall('mod_cc13_'+tag+'_data'):
   values=[int(node.findtext(trig))] if level==2 else [float(node.findtext(trig+'/'+f)) for f in fs]
   children=[dict(trigger=[float(n.findtext('cct_trigger/'+f)) for f in ['start','end']],matrix=[float(x) for x in n.findtext('cc13_rgn_data/c_tab/c').split()],offsets=[int(x) for x in n.findtext('cc13_rgn_data/k_tab/k').split()]) for n in node.findall(child+'/mod_cc13_cct_data')] if level==3 else xml_ccm(node.find(child),level+1)
   out.append(dict(trigger=values,children=children))
  return out
 def xml_ltm(parent,level=0):
  tag,trig,child,fs=axes[[0,1,3][level]];out=[]
  for node in parent.findall('mod_ltm13_'+tag+'_data'):
   row=dict(trigger=[float(node.findtext(trig+'/'+f)) for f in fs])
   if level<2:row['children']=xml_ltm(node.find(child),level+1)
   else:row['data']=xml_fields(node.find('ltm13_rgn_data'),region_fields)
   out.append(row)
  return out
 roots={'ltm13_ipe':[],'cc13_ipe':[]};analysis=bytearray(raw)
 for uid,e in entries.items():
  if e['name'] not in roots:continue
  data=blob(int(uid));words=struct.unpack('<'+str(len(data)//8)+'Q',data)
  if e['name']=='ltm13_ipe':
   assert len(data)==872;row=dict(uid=int(uid),enabled=words[0],control_method=[words[9],words[10]],reserve=read_fields(data,88,reserve_fields),core=ltm(words[-1],words[-2]))
  else:
   assert len(data)==144;row=dict(uid=int(uid),enabled=words[0],control_method=[words[11],words[12]],led_sensitivity_trigger=[struct.unpack_from('<f',data,i*8)[0] for i in [13,14]],qfactor=words[15],core=ccm(words[17],words[16]))
  roots[e['name']].append(row)
 for module,rows in roots.items():(P/(name+'-'+module+'-trees-private.json')).write_text(json.dumps(rows,indent=2)+'\n')
 start,length=next(s[1:] for s in idx['sections'] if s[0]==0)
 for pos in range(start,start+length,72):
  uid=struct.unpack_from('<Q',raw,pos)[0]
  if entries[str(uid)]['name'] not in roots:struct.pack_into('<I',analysis,pos+40,0)
 assert all(analysis[o:o+n]==raw[o:o+n] for kind,o,n in idx['sections'] if kind!=0)
 work=WORK/(name+'-colour-r1');directory=work/'api/isp';dest=work/'xml'
 if not work.exists():
  directory.mkdir(parents=True);(work/'api/common').mkdir();dest.mkdir();os.chmod(work,0o700)
  for source,target in [(P/'sources/ltm_1_3_0.xsd',directory/'ltm_1_3_0.xsd'),(P/'sources/cc_1_3_0.xsd',directory/'cc_1_3_0.xsd'),(P.parent/'kernel298/ispglobalelements.xsd-reference-private',directory/'ispglobalelements.xsd'),(P.parent/'kernel298/globalelements.xsd-reference-private',work/'api/common/globalelements.xsd'),(P.parent/'kernel117/CamxChi/chi-cdk/api/chromatix/XSD/ParameterTuningTypes.xsd',directory/'ParameterTuningTypes.xsd')]:shutil.copyfile(source,target)
  (work/'analysis.bin').write_bytes(analysis)
  for item in [work,*work.rglob('*')]:os.chown(item,1000,1000)
 else:assert (work/'analysis.bin').read_bytes()==analysis
 exit_path=P/(name+'-parser-exit.json')
 if not exit_path.exists():
  reader=Path('/home/cy122/x2pro-linux/parser-k117')
  with (P/(name+'-parser.log')).open('xb') as log:
   q=subprocess.run([str(reader/'ParameterParser'),str(dest),'x',str(directory),'-b'+str(work/'analysis.bin')],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=str(reader/'runtime/lib')),user=1000,group=1000,stdin=subprocess.DEVNULL,stdout=log,stderr=log,timeout=55)
  exit_path.write_text(json.dumps(dict(exit_code=q.returncode)));assert not q.returncode,(name,q.returncode)
 else:assert not json.loads(exit_path.read_text())['exit_code']
 for module,rows in roots.items():
  matches=[]
  for path in dest.rglob(module+'.xml'):
   xml=ET.parse(path).getroot();cc=module=='cc13_ipe'
   row=dict(enabled=int(xml.findtext('enable_section/'+('cc_enable' if cc else 'ltm_enable'))),control_method=methods(xml))
   if cc:row.update(qfactor=int(xml.findtext('chromatix_cc13_reserve/q_factor')),led_sensitivity_trigger=[float(xml.findtext('private_information/led_sensitivity_trigger/'+f)) for f in ['start','end']],core=xml_ccm(xml.find('chromatix_cc13_core')))
   else:row.update(reserve=xml_fields(xml.find('chromatix_ltm13_reserve'),reserve_fields),core=xml_ltm(xml.find('chromatix_ltm13_core')))
   ids=[r['uid'] for r in rows if norm({k:v for k,v in r.items() if k!='uid'})==norm(row)]
   if not ids:
    (P/(name+'-'+module+'-unmatched-xml-private.json')).write_text(json.dumps(row,indent=2)+'\n')
    raise AssertionError((name,str(path)))
   matches.append(dict(selector=path.relative_to(dest).as_posix(),uids=ids))
  assert len(matches)==len(rows) and {r['uid'] for r in rows}=={u for m in matches for u in m['uids']}
  def leaves(nodes):
   for node in nodes:
    if 'children' in node:yield from leaves(node['children'])
    else:yield node
  reports.append(dict(variant=name,module=module,roots=len(rows),regions=sum(len(list(leaves(r['core']))) for r in rows),full_tree_and_reserve_match=True))
  (P/(name+'-'+module+'-xml-matches-private.json')).write_text(json.dumps(matches,indent=2)+'\n')
  print(json.dumps(reports[-1]),flush=True)
source_manifest=[]
for source in (P/'sources').iterdir():
 if source.suffix not in ['.xsd','.xml']:continue
 raw=source.read_bytes();path=('camx/src/hwl/titan17x/' if source.suffix=='.xml' else 'chi-cdk/api/chromatix/XSD/isp/')+source.name
 source_manifest.append(dict(path=path,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),url='https://github.com/bjzhou/CamxChi/blob/9f17f1b568626b393e785b369c5dc94543774d7a/'+path))
(HERE/'primary-sources.json').write_text(json.dumps(dict(stage=351,commit='9f17f1b568626b393e785b369c5dc94543774d7a',files=source_manifest),indent=2)+'\n')
(HERE/'factory-colour-chain-validation.json').write_text(json.dumps(dict(stage=351,sources=reports,source_payload_and_mode_tree_unchanged=True,all_tables_private=True,phone_changed=False,runtime_settings_not_verified=True,passed=True),indent=2)+'\n')
