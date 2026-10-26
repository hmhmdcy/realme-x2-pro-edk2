"""Map the retained full/bin2 modes and prepare explicit factory-only tuning."""
from pathlib import Path
import importlib.util,json,re,xml.etree.ElementTree as ET,yaml
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
xml=P.parent/'kernel239/s5k3m5-b-xml-private/Scenario.0/XML/None/sensorDriverData.xml'
modes=ET.parse(xml).findall('resolutionInfo/resolutionData')
def geometry(mode):
 regs={int(r.findtext('registerAddr')):int(r.findtext('registerData')) for r in mode.iter('regSetting')}
 b=2 if regs[0x900]==0x112 else 1
 return dict(analogue_crop=[regs[0x344],regs[0x346],regs[0x348]-regs[0x344]+1,regs[0x34a]-regs[0x346]+1],
  digital_offset=[regs[0x350],regs[0x352]],binning=[b,b],output=[regs[0x34c],regs[0x34e]],
  reference_origin=[regs[0x344]+regs[0x350]*b,regs[0x346]+regs[0x352]*b]),regs
full,_=geometry(modes[0]);active,regs=geometry(modes[3])
text=Path('/home/cy122/x2pro-linux/camera318-lsc-kernel/drivers/media/i2c/s5k3m5-19mhz-tables.h').read_text().split('s5k3m5_clock19_mode3_regs[] = {')[1]
native={int(a,16):int(b,16) for a,b in re.findall(r'CCI_REG16\(0x([0-9a-f]+)\),\s*0x([0-9a-f]+)',text,re.I)}
keys=[0x344,0x346,0x348,0x34a,0x34c,0x34e,0x350,0x352,0x900,0x380,0x382,0x384,0x386,0x402,0x404]
assert all(native[k]==regs[k] for k in keys)
assert active['analogue_crop']==full['analogue_crop'] and active['reference_origin']==full['reference_origin']
assert [v*2 for v in active['output']]==full['output']
mapping=dict(source_span=[2103.,1559.],first_quad=[0.,0.],quad_step=[2.,2.])
spec=importlib.util.spec_from_file_location('assembler',HERE.parent/'kernel322/assemble-profile.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
roots=json.loads((P/'tele-trigger-trees-private.json').read_text());selectors=json.loads((HERE/'tele-trigger-tree-validation.json').read_text())['selectors']
default=next(r for r in selectors if r['selector']=='Scenario.Default/XML/IFE/lsc34_ife.xml');root=next(r for r in roots if r['uid']==default['binary_uids'][0])
gains,golden=a.assemble(root,100.,6500.,led_index=0)
directory=P/'profiles';directory.mkdir(exist_ok=True)
base=yaml.safe_load((HERE.parent/'kernel313/s5k3m5.yaml').read_text());mode=base['modes'][0]
mode['residual_black_subtraction']=0;mode['range_normalization']=1.
(directory/'off.yaml').write_text(yaml.safe_dump(base,sort_keys=False))
mode['lens_shading']=dict(**mapping,gains=gains)
(directory/'factory.yaml').write_text(yaml.safe_dump(base,sort_keys=False))
cases=0
for r in roots:
 nodes=r['core']
 for _ in range(3):assert len(nodes)==1;nodes=nodes[0]['children']
 nodes=next(n['children'] for n in nodes if n['trigger']==[0])
 values={v for n in nodes for v in n['trigger'][:2]};values.update((n['trigger'][1]+m['trigger'][0])/2 for n,m in zip(nodes,nodes[1:]))
 for v in values:
  for cct in [1000.,2500.,3550.,4550.,6500.,12000.]:
   selected,gold=a.assemble(r,v,cct,led_index=0)
   assert all(len(ch)==221 and min(ch)>0 for table in [selected,gold] for ch in table.values());cases+=1
multiple=next(r for r in roots if r['uid']==625)
try:a.assemble(multiple,100.,6500.)
except ValueError:pass
else:raise AssertionError('implicit multi-LED selection accepted')
assert a.assemble(multiple,100.,6500.,led_index=1)
try:a.assemble(multiple,100.,6500.,led_index=2)
except ValueError:pass
else:raise AssertionError('absent LED branch accepted')
report=dict(stage=323,sensor='s5k3m5',reference_mode=0,active_mode=3,reference_geometry=full,active_geometry=active,
 current_kernel_geometry_matches_stock=True,matching_reference_origin_and_field_of_view=True,
 mapping=mapping,reference_domain='mode0 output following fixed CamX source convention in321',
 exact_target_hal_full_resolution_assignment_not_disassembled=True,
 selector=default['selector'],equivalent_binary_uids=default['binary_uids'],explicit_lux_index=100.,explicit_cct_kelvin=6500.,
 factory_trigger_cases=cases,explicit_led_index=0,illuminator_branch_selection_and_rejection_verified=True,flash_blending_implemented=False,individual_data_applied=False,default_tuning_changed=False,passed=True)
(HERE/'tele-mode-profile-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
