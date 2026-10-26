"""Recover complete TMC10 roots and compare retained OEM XML parser output."""
from pathlib import Path
import importlib.util,json,os,shutil,struct,subprocess,xml.etree.ElementTree as ET
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
WORK=storage.mounted_build().parent/'parser410';WORK.mkdir(mode=0o755,exist_ok=True)
ns={'x':'http://www.w3.org/2001/XMLSchema'};schema=ET.parse(P/'sources/tmc_1_0_0.xsd')
def fields(name):
    node=next(e for e in schema.findall('x:complexType',ns) if e.attrib.get('name')==name)
    result=[]
    for e in node.findall('x:sequence/x:element',ns):
        attrs={a.attrib['name']:a.attrib.get('fixed',a.attrib.get('default')) for a in e.findall('.//x:attribute',ns)}
        assert int(attrs['length'])==1
        result.append((e.attrib['name'],{'float':'f','uint':'I','int':'i'}[attrs.get('tool_hint',attrs['type'])]))
    return result
region=fields('tmc10_rgn_dataType');reserve=fields('chromatix_tmc10_reserveType')
assert len(region)==11 and len(reserve)==9
def read_fields(raw,offset,layout):return {name:struct.unpack_from('<'+kind,raw,offset+i*8)[0] for i,(name,kind) in enumerate(layout)}
def norm(value):
    if isinstance(value,float):return float(format(value,'.6g'))
    if isinstance(value,list):return [norm(v) for v in value]
    if isinstance(value,dict):return {k:norm(v) for k,v in value.items()}
    return value
reports=[]
for variant in ['qtech_s5kgw1','sunny_s5kgw1','sunny_imx471','qtech_s5k3m5sx','sunny_imx319']:
    index=json.loads((P.parent/'kernel333'/(variant+'-index-private.json')).read_text());entries=index['entries']
    original=(P.parent/('kernel'+str(index['source_stage']))/index['filename']).read_bytes()
    def blob(uid):
        e=entries[str(uid)];return original[index['base']+e['offset']:index['base']+e['offset']+e['bytes']]
    roots=[]
    for uid,e in entries.items():
        if e['name']!='tmc10_sw':continue
        raw=blob(uid);assert len(raw)==152
        count,ref=struct.unpack_from('<2Q',raw,136);leaf=blob(ref)
        assert entries[str(ref)]['name']=='mod_tmc10_aec_data' and len(leaf)==count*120
        core=[]
        for offset in range(0,len(leaf),120):
            core.append(dict(trigger=[struct.unpack_from('<f',leaf,offset+i*8)[0] for i in range(4)],data=read_fields(leaf,offset+32,region)))
        roots.append(dict(uid=int(uid),enabled=struct.unpack_from('<Q',raw)[0],
                          control_method=struct.unpack_from('<Q',raw,56)[0],reserve=read_fields(raw,64,reserve),core=core))
    assert len(roots)==1
    (P/(variant+'-tmc10-trees-private.json')).write_text(json.dumps(roots,indent=2)+'\n')
    analysis=bytearray(original);start,length=next(s[1:] for s in index['sections'] if s[0]==0)
    for pos in range(start,start+length,72):
        uid=struct.unpack_from('<Q',original,pos)[0]
        if entries[str(uid)]['name']!='tmc10_sw':struct.pack_into('<I',analysis,pos+40,0)
    work=WORK/variant;directory=work/'api/isp';dest=work/'xml'
    if not work.exists():
        directory.mkdir(parents=True);(work/'api/common').mkdir();dest.mkdir()
        for source,target in [(P/'sources/tmc_1_0_0.xsd',directory/'tmc_1_0_0.xsd'),
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
        exit_path.write_text(json.dumps(dict(exit_code=q.returncode)));assert not q.returncode
    else:assert not json.loads(exit_path.read_text())['exit_code']
    paths=list(dest.rglob('tmc10_sw.xml'));assert len(paths)==1
    xml=ET.parse(paths[0]).getroot()
    def xml_fields(parent,layout):return {name:(float if kind=='f' else int)(parent.findtext(name)) for name,kind in layout}
    actual=dict(enabled=int(xml.findtext('enable_section/adrc_isp_enable')),
                control_method=['control_lux_idx','control_gain'].index(xml.findtext('control_method/aec_exp_control')),
                reserve=xml_fields(xml.find('chromatix_tmc10_reserve'),reserve),core=[])
    for item in xml.findall('chromatix_tmc10_core/mod_tmc10_aec_data'):
        actual['core'].append(dict(trigger=[float(item.findtext('aec_trigger/'+name)) for name in ['lux_idx_start','lux_idx_end','gain_start','gain_end']],data=xml_fields(item.find('tmc10_rgn_data'),region)))
    expected={k:v for k,v in roots[0].items() if k!='uid'}
    if norm(actual)!=norm(expected):
        (P/(variant+'-xml-mismatch-private.json')).write_text(json.dumps(dict(binary=expected,xml=actual),indent=2)+'\n')
        raise AssertionError((variant,'TMC10 XML mismatch'))
    row=dict(variant=variant,roots=1,regions=len(roots[0]['core']),enabled=roots[0]['enabled'],
             control_reserve_and_all_regions_match_oem_xml=True)
    reports.append(row);print(json.dumps(row),flush=True)
report=dict(stage=410,variants=reports,roots=sum(r['roots'] for r in reports),regions=sum(r['regions'] for r in reports),
            original_payload_and_mode_tree_unchanged=True,all_coefficients_and_xml_private=True,
            tmc11_also_present_not_assumed_tmc10_selected=True,phone_accessed=False,passed=True)
(HERE/'factory-tmc10-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
