"""Tie the wide sensor's active reference domain to real register geometry."""
from pathlib import Path
import hashlib,json,re,xml.etree.ElementTree as ET
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
root=ET.parse(P.parent/'kernel235/sunny-vendor-xml/Scenario.0/XML/None/sensorDriverData.xml').getroot()
def geometry(mode):
 regs={int(r.findtext('registerAddr')):int(r.findtext('registerData')) for r in mode.iter('regSetting')}
 word=lambda a:regs[a]*256+regs[a+1]
 analogue=[word(0x344),word(0x346),word(0x348)-word(0x344)+1,word(0x34a)-word(0x346)+1]
 digital=[word(a) for a in [0x408,0x40a,0x40c,0x40e]]
 binxy=regs[0x901] if regs[0x900] else 0x11;binning=[binxy>>4,binxy&15]
 return dict(analogue_crop=analogue,digital_crop=digital,binning=binning,output=[word(0x34c),word(0x34e)],
  native_origin=[analogue[0]+digital[0]*binning[0],analogue[1]+digital[1]*binning[1]],scale_mode=regs[0x401],scale_m=word(0x404)),regs
modes=root.findall('resolutionInfo/resolutionData');full,fullregs=geometry(modes[0]);wide,registers=geometry(modes[2])
header=Path('/home/cy122/x2pro-linux/camera318-lsc-kernel/drivers/media/i2c/imx319-222mhz-tables.h').read_text().split('imx319_222mhz_mode_regs[] = {',1)[1]
native={int(a,16):int(b,16) for a,b in re.findall(r'\{\s*0x([0-9a-f]+),\s*0x([0-9a-f]+)',header,re.I)}
keys=[*range(0x344,0x350),*range(0x408,0x410),0x900,0x901,0x401,0x404,0x405]
assert all(registers[a]==native[a] for a in keys)
assert full['native_origin']==wide['native_origin'] and [wide['output'][i]*wide['binning'][i] for i in range(2)]==full['output']
assert wide['scale_mode']==0 and wide['scale_m']==16
mapping=dict(source_span=[full['output'][0]/2-1,full['output'][1]/2-1],first_quad=[0.,0.],quad_step=[2.,2.])
source=P/'sources/camxifenode.cpp';text=source.read_text()
assert 'm_pSensorModeRes0Data->resolution.outputWidth' in text
report=dict(stage=321,reference_mode=0,active_mode=2,reference_geometry=full,active_geometry=wide,
 current_kernel_geometry_matches_stock=True,matching_physical_field_of_view=True,
 fixed_camx_reference_domain='mode0 output, not entire physical pixel array',mapping=mapping,
 register_analogue_width_divided_by_output_is_not_binning=True,
 primary_source=dict(url='https://raw.githubusercontent.com/comprehensive9/vendor_qcom_proprietary/36fc163a534963a5b3af52186af5efcc63401ad2/camx/src/hwl/ife/camxifenode.cpp',sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
  full_resolution_assignments=[2957,2958,3563,3564],sensor_offset_and_factors=[3555,3556,3559,3560]),
 exact_target_hal_full_resolution_assignment_not_disassembled=True,phone_changed=False)
(HERE/'imx319-mode-mapping-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
