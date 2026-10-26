"""Retain exact HAL payload CCTs separately from factory calibration coordinates."""
from pathlib import Path
import json, struct
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
raw=(P.parent/'kernel316/hal-source/camera.qcom.so').read_bytes()
offset=struct.unpack_from('<Q',raw,0x28)[0];stride,count,strings=struct.unpack_from('<HHH',raw,0x3a)
sections=[struct.unpack_from('<IIQQQQIIQQ',raw,offset+i*stride) for i in range(count)]
table_va=0xdd800
section=next(s for s in sections if s[3]<=table_va and table_va+20<=s[3]+s[5])
table_offset=section[4]+table_va-section[3]
ccts=list(struct.unpack_from('<5I',raw,table_offset))
assert ccts==[6500,3800,2850,5000,2300]
instructions={0x4058d0:0x7100119f,0x4058d8:0x90ffe6cd,0x4058dc:0x912001ad,0x4058e0:0xb86c79b5,
 0x4059ec:0x2900d67b,0x4059f0:0xf940068a,0x4059f4:0xf800c26a,
 0x405a4c:0xb86879d5,0x405af8:0xb86979f5,0x405ba4:0xb86a7a15,0x405c50:0xb86b7a35}
assert all(struct.unpack_from('<I',raw,at)[0]==word for at,word in instructions.items())
unit=json.loads((P/'formatted-unit-wb-private.json').read_text())
validation=json.loads((HERE/'factory-wb-validation.json').read_text())
bundle={};reports=[]
for module in validation['modules']:
 name=module['module'];roots=json.loads((P/(name+'-factory-wb-private.json')).read_text())
 calibration=next(r for r in roots if r['tag']=='sensorCalV1')
 n=calibration['data']['num_of_cal_factors'];assert n==5
 factory_ccts=calibration['data']['cct'][:n]
 payload=[]
 for light in unit[name]:
  i=light['illuminant']
  payload.append(dict(available=True,illuminant=light['illuminant_name'],cct=ccts[i],
   ratio_rg=light['stock_float32_r_over_gb'],ratio_bg=light['stock_float32_b_over_gb']))
 assert len(payload)==5
 differences=[dict(illuminant=light['illuminant_name'],unit_payload_cct=ccts[i],factory_calibration_slot_cct=factory_ccts[i])
  for i,light in enumerate(unit[name]) if ccts[i]!=factory_ccts[i]]
 bundle[name]=dict(factory_roots=roots,unit_payload=payload,
  factory_calibration_cct_slots=factory_ccts,source_binding='explicit diagnostic source selection; main supplier unresolved',
  calibration_correspondence='not automatically paired by slot; retain both CCT coordinate sets',applied=False)
 reports.append(dict(module=name,unit_illuminant_count=5,factory_calibration_factors=n,
  unit_payload_ccts=ccts,factory_calibration_ccts=factory_ccts,coordinate_differences=differences,
  unit_payload_ratios_copied_unchanged=True,automatic_slot_pairing_applied=False))
(P/'wb-reference-bundle-private.json').write_text(json.dumps(bundle,indent=2)+'\n')
report=dict(stage=328,exact_target_hal_function=['0x405878','0x405d84'],
 hal_payload_temperature_table_va=hex(table_va),hal_payload_ccts=ccts,
 instruction_evidence={hex(k):hex(v) for k,v in instructions.items()},modules=reports,
 main_supplier_binding_verified=False,unit_white_balance_applied=False,
 dynamic_cct_estimation_implemented=False,normal_light_optical_calibration=False,phone_changed=False,passed=True)
(HERE/'wb-reference-binding-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
