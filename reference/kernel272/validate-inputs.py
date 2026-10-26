"""Freshly compare fixed OEM binaries, retained XML projections, and driver geometry."""
from pathlib import Path
import hashlib,json,struct,xml.etree.ElementTree as ET
from gw1_data import Description
import host
R=Path(__file__).resolve().parent
def xml_regs(parent):
 result=[]
 for row in parent.findall('regSetting'):
  vals=lambda name:[int(v) for e in row.findall(name) for v in (e.text or '').split()]
  result.append(dict(address=int(row.findtext('registerAddr')),address_bytes=int(row.findtext('regAddrType')),
   value_bytes=int(row.findtext('regDataType')),operation=row.findtext('operation'),values=vals('registerData'),delays_us=vals('delayUs')))
 return result
rows=[];all_modes={}
for variant in ['qtech','sunny']:
 d=Description(variant)
 info=d.words(d.uid('initSettings'));initial=d.regs(info[2],info[1])
 ri=d.words(d.uid('resolutionInfo'));raw=d.payload(ri[3],'resolutionData');assert len(raw)==ri[2]*256
 modes=[]
 for i in range(ri[2]):
  fields=struct.unpack_from('<32Q',raw,i*256);modes.append(d.regs(fields[19],fields[18]))
 direct=json.loads((host.PRIVATE.parent/'kernel270'/('gw1-'+variant+'-direct-registers-private.json')).read_text())
 assert direct==dict(init=initial,modes=modes)
 projections=[]
 for view in ['a','b']:
  path=next((Path('/home/cy122/x2pro-linux')/('parser-k270-gw1-'+variant+'-'+view+'-r2/xml')).rglob('sensorDriverData.xml'))
  root=ET.parse(path).getroot();nodes=root.findall('resolutionInfo/resolutionData')
  assert len(nodes)==len(modes)==10
  for index,node in enumerate(nodes):assert xml_regs(node.find('resSettings'))==modes[index]
  if view=='b':assert xml_regs(root.find('initSettings/initSetting'))==initial
  projections.append(dict(view=view,xml_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),modes_checked=10,init_checked=view=='b'))
 rows.append(dict(variant=variant,source_sha256=hashlib.sha256(d.raw).hexdigest(),projections=projections))
 all_modes[variant]=modes
assert all_modes['qtech']==all_modes['sunny']
geometry=[]
for index in [2,4]:
 regs=all_modes['sunny'][index]
 assert all(r['operation']=='WRITE' and len(r['values'])==1 for r in regs)
 values={r['address']:r['values'][0] for r in regs}
 assert [values[a] for a in [0x0344,0x0348,0x034c,0x0350,0x0352,0x0900,0x0101]]==[32,9247,4608,0,8,0x2222,3]
 assert values[0x034a]-values[0x0346]+1==2*(values[0x034e]+2*values[0x0352])
 crop=[values[0x0344]+2*values[0x0350],values[0x0346]+2*values[0x0352],2*values[0x034c],2*values[0x034e]]
 geometry.append(dict(oem_mode=index,output=[values[0x034c],values[0x034e]],crop=crop,
  crop_interpretation='2x2 binning, digital offset in binned coordinates; physical geometry still pending'))
assert [len(all_modes['sunny'][i]) for i in [1,6]]==[1,1]
report=dict(stage=272,source_and_retained_xml_freshly_rechecked=True,variants=rows,
 both_variants_init_and_all10_mode_tables_equal=True,geometry=geometry,
 incomplete_mode1_and6_are_not_standalone=True,physical_timing_and_geometry_unverified=True,phone_unchanged=True)
(R/'input-revalidation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
