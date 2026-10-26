"""Recover complete TMC11 trees and compare retained OEM ParameterParser XML."""
from pathlib import Path
import importlib.util,json,os,shutil,struct,subprocess,xml.etree.ElementTree as ET
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
WORK=storage.mounted_build().parent/'parser412';WORK.mkdir(mode=0o755,exist_ok=True)
ns={'x':'http://www.w3.org/2001/XMLSchema'};schema=ET.parse(P/'sources/tmc_1_1_0.xsd')

def fields(name):
    result=[];offset=0
    node=next(e for e in schema.findall('x:complexType',ns) if e.attrib.get('name')==name)
    for e in node.findall('x:sequence/x:element',ns):
        attrs={a.attrib['name']:a.attrib.get('fixed',a.attrib.get('default')) for a in e.findall('.//x:attribute',ns)}
        count=int(attrs['length']);kind=attrs.get('tool_hint',attrs['type']);child=None
        if count>1:child=e.find('x:complexType/x:sequence/x:element',ns).attrib['name']
        result.append(dict(name=e.attrib['name'],child=child,count=count,format={'float':'f','uint':'I','int':'i'}[kind],offset=offset))
        offset+=(count*4+7)//8*8
    return result,offset

reserve,reserve_size=fields('chromatix_tmc11_reserveType');region,region_size=fields('tmc11_rgn_dataType')
assert reserve_size==80
def read_fields(raw,offset,layout):
    result={}
    for f in layout:
        values=list(struct.unpack_from('<'+str(f['count'])+f['format'],raw,offset+f['offset']))
        result[f['name']]=values if f['count']>1 else values[0]
    return result
def xml_fields(node,layout):
    result={}
    for f in layout:
        text=node.findtext(f['name']+('/'+f['child'] if f['child'] else ''))
        values=[(float if f['format']=='f' else int)(s) for s in text.split()];assert len(values)==f['count']
        result[f['name']]=values if f['count']>1 else values[0]
    return result
def norm(value):
    if isinstance(value,float):return float(format(value,'.6g'))
    if isinstance(value,list):return [norm(v) for v in value]
    if isinstance(value,dict):return {k:norm(v) for k,v in value.items()}
    return value
axes=[('drc_gain','drc_gain_trigger','drc_gain_data',['start','end']),
      ('hdr_aec','hdr_aec_trigger','hdr_aec_data',['exp_time_start','exp_time_end','aec_sensitivity_start','aec_sensitivity_end','exp_gain_start','exp_gain_end']),
      ('aec','aec_trigger',None,['lux_idx_start','lux_idx_end','gain_start','gain_end'])]
def leaves(nodes):
    for node in nodes:
        if 'children' in node:yield from leaves(node['children'])
        else:yield node
reports=[]
for variant in ['qtech_s5kgw1','sunny_s5kgw1','sunny_imx471','qtech_s5k3m5sx','sunny_imx319']:
    index=json.loads((P.parent/'kernel333'/(variant+'-index-private.json')).read_text());entries=index['entries']
    original=(P.parent/('kernel'+str(index['source_stage']))/index['filename']).read_bytes()
    def blob(uid):
        e=entries[str(uid)];return original[index['base']+e['offset']:index['base']+e['offset']+e['bytes']]
    def tree(uid,count,level=0):
        tag,trig,child,names=axes[level];assert entries[str(uid)]['name']=='mod_tmc11_'+tag+'_data'
        data=blob(uid);stride=(len(names)+2)*8 if level<2 else len(names)*8+region_size
        assert len(data)==count*stride,(variant,uid,count,len(data),stride)
        result=[]
        for off in range(0,len(data),stride):
            row=dict(trigger=[struct.unpack_from('<f',data,off+i*8)[0] for i in range(len(names))])
            if level<2:
                n,ref=struct.unpack_from('<2Q',data,off+len(names)*8);row['children']=tree(ref,n,level+1)
            else:row['data']=read_fields(data,off+len(names)*8,region)
            result.append(row)
        return result
    def xml_tree(parent,level=0):
        tag,trig,child,names=axes[level];result=[]
        for node in parent.findall('mod_tmc11_'+tag+'_data'):
            row=dict(trigger=[float(node.findtext(trig+'/'+n)) for n in names])
            if level<2:row['children']=xml_tree(node.find(child),level+1)
            else:row['data']=xml_fields(node.find('tmc11_rgn_data'),region)
            result.append(row)
        return result
    roots=[]
    for uid,e in entries.items():
        if e['name']!='tmc11_sw':continue
        raw=blob(uid);assert len(raw)==184
        words=struct.unpack('<23Q',raw)
        roots.append(dict(uid=int(uid),enabled=words[0],control_method=[words[9],words[10]],
                          reserve=read_fields(raw,88,reserve),core=tree(words[22],words[21])))
    assert roots
    (P/(variant+'-tmc11-trees-private.json')).write_text(json.dumps(roots,indent=2)+'\n')
    analysis=bytearray(original);start,length=next(s[1:] for s in index['sections'] if s[0]==0)
    for pos in range(start,start+length,72):
        uid=struct.unpack_from('<Q',original,pos)[0]
        if entries[str(uid)]['name']!='tmc11_sw':struct.pack_into('<I',analysis,pos+40,0)
    assert all(analysis[o:o+n]==original[o:o+n] for kind,o,n in index['sections'] if kind!=0)
    work=WORK/variant;directory=work/'api/isp';dest=work/'xml'
    if not work.exists():
        directory.mkdir(parents=True);(work/'api/common').mkdir();dest.mkdir();os.chmod(work,0o700)
        for source,target in [(P/'sources/tmc_1_1_0.xsd',directory/'tmc_1_1_0.xsd'),
                              (P.parent/'kernel298/ispglobalelements.xsd-reference-private',directory/'ispglobalelements.xsd'),
                              (P.parent/'kernel298/globalelements.xsd-reference-private',work/'api/common/globalelements.xsd'),
                              (P.parent/'kernel117/CamxChi/chi-cdk/api/chromatix/XSD/ParameterTuningTypes.xsd',directory/'ParameterTuningTypes.xsd')]:shutil.copyfile(source,target)
        (work/'analysis.bin').write_bytes(analysis)
        for item in [work,*work.rglob('*')]:os.chown(item,1000,1000)
    else:assert (work/'analysis.bin').read_bytes()==analysis
    exit_path=P/(variant+'-parser-exit.json')
    if not exit_path.exists():
        reader=Path('/home/cy122/x2pro-linux/parser-k117')
        with (P/(variant+'-parser.log')).open('xb') as log:
            q=subprocess.run([str(reader/'ParameterParser'),str(dest),'x',str(directory),'-b'+str(work/'analysis.bin')],cwd=work,
                env=dict(os.environ,LD_LIBRARY_PATH=str(reader/'runtime/lib')),user=1000,group=1000,stdin=subprocess.DEVNULL,stdout=log,stderr=log,timeout=55)
        exit_path.write_text(json.dumps(dict(exit_code=q.returncode)));assert not q.returncode,(variant,q.returncode)
    else:assert not json.loads(exit_path.read_text())['exit_code']
    matches=[]
    for path in dest.rglob('tmc11_sw.xml'):
        xml=ET.parse(path).getroot();methods=xml.find('control_method')
        row=dict(enabled=int(xml.findtext('enable_section/tmc_enable')),
            control_method=[['control_lux_idx','control_gain'].index(methods.findtext('aec_exp_control')),
                            ['control_exp_time_ratio','control_aec_exp_sensitivity_ratio','control_exp_gain_ratio'].index(methods.findtext('aec_hdr_control'))],
            reserve=xml_fields(xml.find('chromatix_tmc11_reserve'),reserve),core=xml_tree(xml.find('chromatix_tmc11_core')))
        ids=[r['uid'] for r in roots if norm({k:v for k,v in r.items() if k!='uid'})==norm(row)]
        if not ids:
            (P/(variant+'-unmatched-xml-private.json')).write_text(json.dumps(row,indent=2)+'\n');raise AssertionError((variant,str(path)))
        matches.append(dict(selector=path.relative_to(dest).as_posix(),uids=ids))
    assert len(matches)==len(roots) and {r['uid'] for r in roots}=={u for m in matches for u in m['uids']}
    (P/(variant+'-xml-matches-private.json')).write_text(json.dumps(matches,indent=2)+'\n')
    row=dict(variant=variant,roots=len(roots),enabled_roots=sum(bool(r['enabled']) for r in roots),
        regions=sum(len(list(leaves(r['core']))) for r in roots),all_control_reserve_and_drc_hdr_aec_regions_match_oem_xml=True)
    reports.append(row);print(json.dumps(row),flush=True)
result=dict(stage=412,variants=reports,roots=sum(r['roots'] for r in reports),regions=sum(r['regions'] for r in reports),
    region_fields=len(region),region_scalars=sum(f['count'] for f in region),region_binary_stride=region_size,
    original_payload_and_mode_tree_unchanged=True,all_tables_and_xml_private=True,root_enable_not_changed=True,
    runtime_version_not_inferred_from_root_presence=True,phone_accessed=False,passed=True)
(HERE/'factory-tmc11-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
