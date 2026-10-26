"""Cross-check fixed original facts against the actual constant and pixel responses."""
from pathlib import Path
import hashlib,json,struct

ROOT=Path(__file__).resolve().parent
data=Path('/mnt/e/edk2-samurai-out/kernel281/camera.qcom.so-private').read_bytes()
assert hashlib.sha256(data).hexdigest()=='e2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde'
offset=struct.unpack_from('<Q',data,32)[0];size,count=struct.unpack_from('<HH',data,54);loads=[]
for i in range(count):
 kind,flags,start,address,physical,length,memsize,align=struct.unpack_from('<IIQQQQQQ',data,offset+i*size)
 if kind==1:loads.append((address,start,length))
def word(address):
 for base,start,length in loads:
  if base<=address and address+4<=base+length:return struct.unpack_from('<I',data,start+address-base)[0]
 raise AssertionError(hex(address))
expected={0x2a8b24:0x331d0317,0x2a8b30:0x331c0337,0x2a8b34:0xb903ca77,0x2a98d0:0x52800981}
for address,value in expected.items():assert word(address)==value,hex(address)
refs=json.loads((ROOT/'crop-reference-validation.json').read_text());assert all(r['read'] for r in refs['files'])
crop=Path('/mnt/e/edk2-samurai-out/kernel290/reference-camxifecrop10.cpp-private').read_text()
assert 'videoProcessingModules.CropEnable = m_moduleEnable' in crop
a=json.loads((ROOT/'cst-response-validation.json').read_text());b=json.loads((ROOT/'cst-route-validation.json').read_text())
assert a['frames']==b['frames']==93 and a['graph_restored'] and b['graph_restored'] and b['inactive_gamma_lut_restore_readback_words']==192
for n,value in [(1,128),(2,256),(3,512),(4,1023),(9,512),(10,128),(11,256)]:
 for ch in ['y','u','v']:
  assert a['phases'][n][ch]['min']==a['phases'][n][ch]['max']==value%256
  assert b['phases'][n][ch]['min']==b['phases'][n][ch]['max']==min(255,(value+2)//4)
for n,value in [(12,128),(13,64),(14,0)]:
 for ch in ['y','u','v']:assert b['phases'][n][ch]['min']==b['phases'][n][ch]['max']==value
pixels=json.loads((ROOT/'route-pixel-validation.json').read_text());assert pixels['black_white_neutrality_passed'] and pixels['expected_green_magenta_response_consistent']
report=dict(stage=290,hal_sha256=hashlib.sha256(data).hexdigest(),checked_instruction_addresses=[hex(x) for x in expected],
 full_postprocessing_gate='0x4c bit4',mnds_gate_retained='0x4c bit3',cst_gate_retained='0x4c bit0',
 original_full_client_numbers_y_c=[3,4],original_nv12_packer_unchanged='0xe',
 low_byte_wrap_without_route_reproduced=True,correct_10_to_8_scaling_with_route=True,full_output_clamp_response_verified=True,
 cst_offset_field_reversal_not_needed=True,black_white_and_green_magenta_response_passed=True,
 independent_red_blue_input_validation_still_required=True,physical_camera_quality_not_claimed=True,
 no_downloaded_code_execution=True,no_oem_implementation_copied=True)
(ROOT/'full-route-contract-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
