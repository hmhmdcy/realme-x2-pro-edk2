"""Preserve the optional resolution reference instead of inlining its payload."""
from pathlib import Path
here=Path(__file__).resolve().parent
source=(here/'crosscheck-modes-r2.py').read_text()
source=source.replace("parser-k217-modes-r2","parser-k217-modes-r3").replace('vendor-mode-r2','vendor-mode-r3').replace('vendor-r2-xml','vendor-r3-xml')
old="projection=original[data_offset:data_offset+128]+original[data_offset+entries[14]['relative']:data_offset+entries[14]['relative']+32];assert len(projection)==160"
new="""resolution_node=next(node for node in kept if node.attrib['name']=='resolutionInfo');assert resolution_node.attrib.get('minOccurs')=='0'
projection=original[data_offset:data_offset+128]+struct.pack('<QQ',1,14);assert len(projection)==144"""
assert old in source;source=source.replace(old,new).replace('new_offset,160','new_offset,144').replace('context_prefix_and_resolution_projection_bytes=160','context_prefix_and_resolution_projection_bytes=144')
source=source.replace("print(json.dumps(record));print((private/'vendor-mode-r3-private.log').read_text()[-1000:])","print(json.dumps(record));print((private/'vendor-mode-r3-private.log').read_text()[-1000:]);sensorxml=[p for p in xmls if p.name=='sensorDriverData.xml'];assert len(sensorxml)==1;root=ET.parse(sensorxml[0]).getroot();modes=root.findall('resolutionInfo/resolutionData');assert len(modes)==3;print('Independent vendor reader exported all three resolution modes')")
exec(compile(source,'mode-r3-analysis-projection','exec'))
