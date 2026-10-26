"""Prepare explicit main/front factory profiles with real mode coordinate maps."""
from pathlib import Path
import copy,importlib.util,json,re,xml.etree.ElementTree as ET,yaml
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
kernel=Path('/home/cy122/x2pro-linux/camera318-lsc-kernel/drivers/media/i2c')
spec=importlib.util.spec_from_file_location('assembler',HERE.parent/'kernel322/assemble-profile.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
def regs(mode):return {int(n.findtext('registerAddr')):int(n.findtext('registerData')) for n in mode.iter('regSetting')}
def samsung(r):
 b=1 if r[0x900]==0x11 else 2 if r[0x900]==0x2222 else None;assert b
 return dict(output=[r[0x34c],r[0x34e]],analogue_crop=[r[0x344],r[0x346],r[0x348]-r[0x344]+1,r[0x34a]-r[0x346]+1],binning=[b,b],digital_offset=[r[0x350],r[0x352]],origin=[r[0x344]+r[0x350]*b,r[0x346]+r[0x352]*b])
def sony(r):
 w=lambda k:r[k]*256+r[k+1];b=r[0x901] if r[0x900] else 0x11;assert b in [0x11,0x22]
 bx,by=b>>4,b&15
 return dict(output=[w(0x34c),w(0x34e)],analogue_crop=[w(0x344),w(0x346),w(0x348)-w(0x344)+1,w(0x34a)-w(0x346)+1],binning=[bx,by],digital_offset=[w(0x408),w(0x40a)],origin=[w(0x344)+w(0x408)*bx,w(0x346)+w(0x40a)*by])
main_xml=next(Path('/home/cy122/x2pro-linux/parser-k270-gw1-sunny-b-r2/xml').rglob('sensorDriverData.xml'))
main_modes=ET.parse(main_xml).findall('resolutionInfo/resolutionData');full_main=samsung(regs(main_modes[0]))
front_xml=P.parent/'kernel217/vendor-r4-xml/Scenario.0/XML/None/sensorDriverData.xml'
front_modes=ET.parse(front_xml).findall('resolutionInfo/resolutionData');full_front=sony(regs(front_modes[0]))
maps={};rows=[]
text=(kernel/'s5kgw1-tables.h').read_text();main_keys=[0x344,0x346,0x348,0x34a,0x34c,0x34e,0x350,0x352,0x900]
for index in [2,4]:
 r=regs(main_modes[index]);body=text.split('s5kgw1_mode'+str(index)+'_regs[] = {')[1].split('};')[0]
 current={int(k,16):int(v,16) for k,v in re.findall(r'\.address = 0x([0-9a-f]+), \.value = 0x([0-9a-f]+)',body,re.I)}
 assert all(current[k]==r[k] for k in main_keys)
 g=samsung(r);mapping=dict(source_span=[(v-2)/2 for v in full_main['output']],first_quad=[(g['origin'][i]-full_main['origin'][i])/2 for i in range(2)],quad_step=[float(v) for v in g['binning']])
 maps[('s5kgw1',*g['output'])]=mapping
 rows.append(dict(sensor='s5kgw1',active_mode=index,reference_geometry=full_main,active_geometry=g,mapping=mapping,current_geometry_registers_match=True))
text=(kernel/'imx471.c').read_text();front_keys=[*range(0x344,0x350),*range(0x408,0x410),0x900,0x901]
body=text.split('mode_2304x1728_factory_regs[] = {')[1].split('};')[0]
current={int(k,16):int(v,16) for k,v in re.findall(r'CCI_REG8\(0x([0-9a-f]+)\),\s*0x([0-9a-f]+)',body,re.I)}
r=regs(front_modes[1]);assert all(current[k]==r[k] for k in front_keys)
g=sony(r)
maps[('imx471',*g['output'])]=dict(source_span=[2303.,1727.],first_quad=[0.,0.],quad_step=[2.,2.])
rows.append(dict(sensor='imx471',active_mode=1,reference_geometry=full_front,active_geometry=g,mapping=maps[('imx471',*g['output'])],current_geometry_registers_match=True))
# The legacy cropped mode uses 16-bit CCI macros; decode those directly.
macros={name:(int(bits),int(address,16)) for name,bits,address in re.findall(r'#define\s+(IMX471_\w+)\s+CCI_REG(8|16)\((0x[0-9a-f]+)\)',text,re.I)}
constants={name:int(value,0) for name,value in re.findall(r'#define\s+(IMX471_\w+)\s+(0x[0-9a-f]+|[0-9]+)\b',text,re.I)}
body=text.split('mode_1928x1088_regs[] = {')[1].split('};')[0];crop_regs={}
for name,value in re.findall(r'\{\s*(IMX471_\w+),\s*(0x[0-9a-f]+|[0-9]+|IMX471_\w+)\s*\}',body,re.I):
 if name not in macros:continue
 bits,addr=macros[name];number=constants[value] if value.startswith('IMX471_') else int(value,0)
 if bits==16:crop_regs[addr]=number>>8;crop_regs[addr+1]=number&255
 else:crop_regs[addr]=number
g=sony(crop_regs);assert g['output']==[1928,1088]
mapping=dict(source_span=[2303.,1727.],first_quad=[(g['origin'][i]-full_front['origin'][i])/2 for i in range(2)],quad_step=[2.,2.])
maps[('imx471',*g['output'])]=mapping
rows.append(dict(sensor='imx471',active_mode='current upstream-derived crop',reference_geometry=full_front,active_geometry=g,mapping=mapping,current_geometry_registers_decoded=True))
directory=P/'profiles';directory.mkdir(exist_ok=True);sources=json.loads((HERE/'factory-lsc-validation.json').read_text())['sources'];profiles=[]
for model in ['s5kgw1','imx471']:
 base=yaml.safe_load((HERE.parent/'kernel313'/(model+'.yaml')).read_text())
 for m in base['modes']:m['residual_black_subtraction']=0;m['range_normalization']=1.
 (directory/(model+'-off.yaml')).write_text(yaml.safe_dump(base,sort_keys=False))
 for source in [s for s in sources if s['name'].endswith(model)]:
  roots=json.loads((P/(source['name']+'-trees-private.json')).read_text());selection=next(s for s in source['selectors'] if s['selector']=='Scenario.Default/XML/IFE/lsc34_ife.xml')
  root=next(r for r in roots if r['uid']==selection['binary_uids'][0]);gain,golden=a.assemble(root,100.,6500.,led_index=0)
  profile=copy.deepcopy(base)
  for m in profile['modes']:
   match=m['match'];m['lens_shading']=dict(**maps[(model,match['width'],match['height'])],gains=copy.deepcopy(gain))
  (directory/(source['name']+'.yaml')).write_text(yaml.safe_dump(profile,sort_keys=False))
  profiles.append(dict(name=source['name'],sensor_model=model,root_uid=root['uid'],selector=selection['selector'],modes=len(profile['modes'])))
report=dict(stage=324,modes=rows,profiles=profiles,explicit_lux_index=100.,explicit_cct_kelvin=6500.,explicit_led_index=0,
 reference_domain='mode0 output following fixed CamX source convention in321',exact_target_hal_full_resolution_assignment_not_disassembled=True,
 imx471_full_mode_software_remosaic_not_enabled=True,individual_values_applied=False,module_supplier_not_yet_bound=True,default_tuning_changed=False,passed=True)
(HERE/'mode-profile-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(stage=324,mappings=[dict(sensor=r['sensor'],output=r['active_geometry']['output'],mapping=r['mapping']) for r in rows],profiles=profiles,passed=True),indent=2))
