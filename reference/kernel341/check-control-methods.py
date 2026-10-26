from pathlib import Path
import json,xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent;rows=[]
sources=json.loads((HERE.parent/'kernel324/factory-lsc-validation.json').read_text())['sources']
for source in sources:
 selected=next(r for r in source['selectors'] if r['selector']=='Scenario.Default/XML/IFE/lsc34_ife.xml')
 rows.append(dict(variant=source['name'],control_method=selected['control_method'],rolloff_enable=selected['rolloff_enable'],evidence='../kernel324/factory-lsc-validation.json'))
for variant,work in [('sunny_imx319','parser-k317-lsc-r1'),('qtech_s5k3m5sx','parser-k323-tele-lsc-r1')]:
 p=Path('/home/cy122/x2pro-linux')/work/'xml/Scenario.Default/XML/IFE/lsc34_ife.xml';root=ET.parse(p).getroot();method={c.tag:c.text for c in root.find('control_method')};enabled=int(root.findtext('enable_section/rolloff_enable'));rows.append(dict(variant=variant,control_method=method,rolloff_enable=enabled,evidence='retained original-parser Default XML'))
for row in rows:assert row['control_method']==dict(aec_exp_control='control_lux_idx',aec_hdr_control='control_aec_exp_sensitivity_ratio') and row['rolloff_enable']==1,row
(HERE/'control-method-validation.json').write_text(json.dumps(dict(stage=341,default_lsc_axes_match_retained_factory_xml=True,rows=rows,physical_mode_supplier_binding_verified=False,passed=True),indent=2)+'\n');print(json.dumps(rows))
