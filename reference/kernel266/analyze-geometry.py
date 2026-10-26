"""Analyze only public geometry/register semantics and non-personal module mounting scalars."""
from pathlib import Path
import hashlib,json,re,xml.etree.ElementTree as ET
import host
R=Path(__file__).parent;B=R.parent/'kernel235';s=(B/'imx319.c').read_text();oem=(B/'imx319-oem-tables.h').read_text();module=[]
for vendor in ['qtech','sunny']:
 p=host.PRIVATE.parent/'kernel192/vendor-prefix-xml'/('com.qti.sensormodule.'+vendor+'_imx319.bin')/'Scenario.0/XML/None/cameraModuleData.xml'
 root=ET.parse(p).getroot();values=[]
 for elem in root.iter():
  name=elem.tag.split('}')[-1]
  if re.search('angle|orient|position|rotation|sensorName',name,re.I) and (elem.text or '').strip():values.append(dict(field=name,value=elem.text.strip()))
 module.append(dict(vendor=vendor,source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),mounting=values))
arrays=re.findall(r'static const struct imx319_reg (mode_\w+_regs)\[\] = \{(.*?)\n\};',s,re.S)
arrays.append(('imx319_oem_mode_regs',oem.split('static const struct imx319_reg imx319_oem_mode_regs[] = {',1)[1].split('};',1)[0]))
modes=[]
for name,body in arrays:
 regs={int(a,16):int(b,16) for a,b in re.findall(r'\{\s*0x([0-9a-f]+),\s*0x([0-9a-f]+)\s*\}',body,re.I)}
 def word(a):return (regs[a]<<8)|regs[a+1]
 x,y,xe,ye=[word(a) for a in [0x344,0x346,0x348,0x34a]]
 digital=[word(a) for a in [0x408,0x40a,0x40c,0x40e]]
 binxy=regs.get(0x901,0x11) if regs.get(0x900,0) else 0x11
 modes.append(dict(name=name,analogue_crop=dict(left=x,top=y,width=xe-x+1,height=ye-y+1),binning=[binxy>>4,binxy&15],digital_crop=digital,output=[word(0x34c),word(0x34e)],scaling_mode=regs.get(0x401),scaling_m=word(0x404)))
private=dict(module_sources=module,modes=modes);(host.PRIVATE/'geometry-and-mounting-private.json').write_text(json.dumps(private,indent=2)+'\n')
report=dict(stage=266,module_mounting=module,register_geometry=modes,native_size_from_supported_full_readout=[3280,2464],hardware_unchanged=True)
(R/'geometry-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

