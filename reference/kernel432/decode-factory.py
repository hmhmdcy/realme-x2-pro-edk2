"""Recover GTM roots/trigger trees and cross-check retained OEM parser XML."""
from pathlib import Path
import importlib.util,json,os,shutil,struct,subprocess,sys,xml.etree.ElementTree as ET
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage432decode',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);WORK=m.mounted_build().parent/'parser432';WORK.mkdir(mode=0o755,exist_ok=True)
ns={'x':'http://www.w3.org/2001/XMLSchema'};schema=ET.parse(P/'sources/gtm_1_0_0.xsd')
def fields(name):
 result=[];offset=0
 node=next(e for e in schema.findall('x:complexType',ns) if e.attrib.get('name')==name)
 for e in node.findall('x:sequence/x:element',ns):
  attrs={a.attrib['name']:a.attrib.get('fixed',a.attrib.get('default')) for a in e.findall('.//x:attribute',ns)}
  count=int(attrs['length']);kind=attrs.get('tool_hint',attrs['type']);child=e.find('x:complexType/x:sequence/x:element',ns).attrib['name'] if count>1 else None
  result.append(dict(name=e.attrib['name'],child=child,count=count,format={'float':'f','uint':'I','int':'i'}[kind],offset=offset));offset+=(count*4+7)//8*8
 return result,offset
reserve,reserve_size=fields('chromatix_gtm10_reserveType');region,region_size=fields('gtm10_rgn_dataType');assert reserve_size==16
def read_fields(raw,off,layout):
 result={}
 for f in layout:
  values=list(struct.unpack_from('<'+str(f['count'])+f['format'],raw,off+f['offset']));result[f['name']]=values if f['count']>1 else values[0]
 return result
def xml_fields(node,layout):
 result={}
 for f in layout:
  text=node.findtext(f['name']+('/'+f['child'] if f['child'] else ''));values=[(float if f['format']=='f' else int)(x) for x in text.split()];assert len(values)==f['count'];result[f['name']]=values if f['count']>1 else values[0]
 return result
def norm(v):
 if isinstance(v,float):return float(format(v,'.6g'))
 if isinstance(v,list):return [norm(x) for x in v]
 if isinstance(v,dict):return {k:norm(x) for k,x in v.items()}
 return v
axes=[('drc_gain','drc_gain_trigger','drc_gain_data',['start','end']),('hdr_aec','hdr_aec_trigger','hdr_aec_data',['exp_time_start','exp_time_end','aec_sensitivity_start','aec_sensitivity_end','exp_gain_start','exp_gain_end']),('aec','aec_trigger',None,['lux_idx_start','lux_idx_end','gain_start','gain_end'])]
def leaves(nodes):
 for node in nodes:
  if 'children' in node:yield from leaves(node['children'])
  else:yield node
reports=[];variants=sys.argv[1:] or ['sunny_s5kgw1','sunny_imx471','qtech_s5k3m5sx','sunny_imx319']
for variant in variants:
 index=json.loads((P.parent/'kernel333'/(variant+'-index-private.json')).read_text());entries=index['entries'];original=(P.parent/('kernel'+str(index['source_stage']))/index['filename']).read_bytes()
 def blob(uid):
  e=entries[str(uid)];return original[index['base']+e['offset']:index['base']+e['offset']+e['bytes']]
 def tree(uid,count,level=0):
  tag,trig,child,names=axes[level];assert entries[str(uid)]['name']=='mod_gtm10_'+tag+'_data'
  data=blob(uid);stride=(len(names)+2)*8 if level<2 else len(names)*8+region_size;assert len(data)==count*stride,(variant,uid,count,len(data),stride)
  rows=[]
  for off in range(0,len(data),stride):
   row=dict(trigger=[struct.unpack_from('<f',data,off+i*8)[0] for i in range(len(names))])
   if level<2:n,ref=struct.unpack_from('<2Q',data,off+len(names)*8);row['children']=tree(ref,n,level+1)
   else:row['data']=read_fields(data,off+len(names)*8,region)
   rows.append(row)
  return rows
 def xml_tree(parent,level=0):
  tag,trig,child,names=axes[level];rows=[]
  for node in parent.findall('mod_gtm10_'+tag+'_data'):
   row=dict(trigger=[float(node.findtext(trig+'/'+n)) for n in names]);row['children' if level<2 else 'data']=xml_tree(node.find(child),level+1) if level<2 else xml_fields(node.find('gtm10_rgn_data'),region);rows.append(row)
  return rows
 roots=[]
 for uid,e in entries.items():
  if e['name'] not in ['gtm10_ife','gtm10_bps']:continue
  data=blob(uid);assert len(data)==120,(uid,len(data));words=struct.unpack('<15Q',data)
  roots.append(dict(uid=int(uid),tag=e['name'],enabled=words[0],control_method=[words[9],words[10]],reserve=read_fields(data,88,reserve),core=tree(words[14],words[13])))
 assert roots;(P/(variant+'-gtm-trees-private.json')).write_text(json.dumps(roots,indent=2)+'\n')
 analysis=bytearray(original);start,length=next(s[1:] for s in index['sections'] if s[0]==0)
 for pos in range(start,start+length,72):
  uid=struct.unpack_from('<Q',original,pos)[0]
  if entries[str(uid)]['name'] not in ['gtm10_ife','gtm10_bps']:struct.pack_into('<I',analysis,pos+40,0)
 assert all(analysis[o:o+n]==original[o:o+n] for kind,o,n in index['sections'] if kind!=0)
 work=WORK/variant;directory=work/'api/isp';dest=work/'xml'
 if not work.exists():
  directory.mkdir(parents=True);(work/'api/common').mkdir();dest.mkdir();os.chmod(work,0o700)
  for source,target in [(P/'sources/gtm_1_0_0.xsd',directory/'gtm_1_0_0.xsd'),(P.parent/'kernel298/ispglobalelements.xsd-reference-private',directory/'ispglobalelements.xsd'),(P.parent/'kernel298/globalelements.xsd-reference-private',work/'api/common/globalelements.xsd'),(P.parent/'kernel117/CamxChi/chi-cdk/api/chromatix/XSD/ParameterTuningTypes.xsd',directory/'ParameterTuningTypes.xsd')]:shutil.copyfile(source,target)
  (work/'analysis.bin').write_bytes(analysis)
  for item in [work,*work.rglob('*')]:os.chown(item,1000,1000)
 else:assert (work/'analysis.bin').read_bytes()==analysis
 exit_path=P/(variant+'-parser-exit-private.json')
 if not exit_path.exists():
  reader=Path('/home/cy122/x2pro-linux/parser-k117')
  with (P/(variant+'-parser-private.log')).open('xb') as log:q=subprocess.run([str(reader/'ParameterParser'),str(dest),'x',str(directory),'-b'+str(work/'analysis.bin')],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=str(reader/'runtime/lib')),user=1000,group=1000,stdin=subprocess.DEVNULL,stdout=log,stderr=log,timeout=55)
  exit_path.write_text(json.dumps(dict(exit_code=q.returncode)));assert not q.returncode
 else:assert not json.loads(exit_path.read_text())['exit_code']
 matched=[]
 for tag in ['gtm10_ife','gtm10_bps']:
  for path in dest.rglob(tag+'.xml'):
   x=ET.parse(path).getroot();control=x.find('control_method');row=dict(tag=tag,enabled=int(x.findtext('enable_section/gtm_enable')),control_method=[['control_lux_idx','control_gain'].index(control.findtext('aec_exp_control')),['control_exp_time_ratio','control_aec_exp_sensitivity_ratio','control_exp_gain_ratio'].index(control.findtext('aec_hdr_control'))],reserve=xml_fields(x.find('chromatix_gtm10_reserve'),reserve),core=xml_tree(x.find('chromatix_gtm10_core')))
   ids=[r['uid'] for r in roots if norm({k:v for k,v in r.items() if k!='uid'})==norm(row)];assert ids,(variant,path)
   matched.append(dict(selector=path.relative_to(dest).as_posix(),uids=ids))
 assert len(matched)==len(roots) and {r['uid'] for r in roots}=={uid for row in matched for uid in row['uids']}
 report=dict(variant=variant,roots=len(roots),enabled_roots=sum(bool(r['enabled']) for r in roots),regions=sum(len(list(leaves(r['core']))) for r in roots),all_binary_fields_trigger_trees_and_enables_match_oem_xml=True,passed=True)
 (HERE/(variant+'-gtm-extraction-validation.json')).write_text(json.dumps(report,indent=2)+'\n');reports.append(report);print(json.dumps(report),flush=True)
r=dict(stage=432,variants=reports,roots=sum(r['roots'] for r in reports),regions=sum(r['regions'] for r in reports),region_fields=len(region),region_scalars=sum(f['count'] for f in region),region_binary_stride=region_size,root_enable_and_original_payload_not_changed=True,all_tables_and_xml_private=True,phone_accessed=False,passed=True)
(HERE/'factory-gtm-validation.json').write_text(json.dumps(r,indent=2)+'\n');(P/'gtm-layout-private.json').write_text(json.dumps(dict(region=region,reserve=reserve),indent=2)+'\n');print(json.dumps(r,indent=2))
