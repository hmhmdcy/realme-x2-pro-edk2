"""Inspect existing independently cross-checked OEM inputs without powering hardware."""
from pathlib import Path
import hashlib,json,re,struct,xml.etree.ElementTree as ET
import host
R=Path(__file__).resolve().parent
proof=json.loads((R.parent/'kernel270/gw1-crosscheck-validation.json').read_text())
assert proof['both_module_variants_crosschecked'] and proof['two_views_each']
rows=[]
for variant in ['qtech','sunny']:
 work=Path('/home/cy122/x2pro-linux')/('parser-k270-gw1-'+variant+'-b-r2/xml')
 xmls=list(work.rglob('sensorDriverData.xml'));assert len(xmls)==1
 root=ET.parse(xmls[0]).getroot()
 def flatten(e):
  if not list(e):return (e.text or '').strip()
  result={}
  for child in e:
   if child.tag in result:
    if not isinstance(result[child.tag],list):result[child.tag]=[result[child.tag]]
    result[child.tag].append(flatten(child))
   else:result[child.tag]=flatten(child)
  return result
 direct=json.loads((host.PRIVATE.parent/'kernel270'/('gw1-'+variant+'-direct-registers-private.json')).read_text())
 row=dict(variant=variant,top_level=[e.tag for e in root],slave_info=flatten(root.find('slaveInfo')),
  init=[dict(address=hex(x['address']),operation=x['operation'],value_bytes=x['value_bytes'],values_count=len(x['values']),first_values=x['values'][:5],delays_us=x['delays_us']) for x in direct['init']],modes=[])
 for i,regs in enumerate(direct['modes']):
  singles={hex(x['address']):x['values'][0] for x in regs if x['operation']=='WRITE' and len(x['values'])==1}
  row['modes'].append(dict(index=i,records=len(regs),bursts=[dict(address=hex(x['address']),value_bytes=x['value_bytes'],count=len(x['values']),first_values=x['values'][:5]) for x in regs if x['operation']!='WRITE'],timing={k:v for k,v in singles.items() if int(k,16) in [0x100,0x112,0x114,0x202,0x204,0x340,0x342,0x344,0x346,0x348,0x34a,0x34c,0x34e,0x902,0x900,0x904,0x116,0x301,0x302,0x304,0x306,0x308,0x30a,0x30c,0x30e,0x310]}))
 rows.append(row)
down=Path('/home/cy122/workspace/realmeX2pro-AndroidR-droidspaces/source/arch/arm64/boot/dts/19781/sm8150-camera-sensor-mtp.dtsi')
text=down.read_text();clean=re.sub(r'/\*.*?\*/|//[^\n]*','',text,flags=re.S)
blocks=[]
for m in re.finditer(r'qcom,cam-sensor@0\s*\{',clean):
 depth=1;i=m.end()
 while depth:
  depth+=int(clean[i]=='{')-int(clean[i]=='}');i+=1
 blocks.append(clean[m.end():i-1])
assert len(blocks)==1
(host.PRIVATE/'gw1-board-node-private.dtsi').write_text(blocks[0])
out=dict(stage=272,variants=rows,downstream_board_sha256=hashlib.sha256(text.encode()).hexdigest(),board_node=blocks[0],no_hardware_operation=True)
(host.PRIVATE/'gw1-contract-inspection-private.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
