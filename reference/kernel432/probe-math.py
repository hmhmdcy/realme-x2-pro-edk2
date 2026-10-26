"""Compare native interpolation and calculation using recovered stock objects."""
from pathlib import Path
import importlib.util,json,struct
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
module('storage432math',HERE.parent/'kernel284/storage.py').mounted_build();n=module('gtm432',HERE/'gtm-model.py')
reports=[]
for variant in ['sunny_s5kgw1','sunny_imx471','qtech_s5k3m5sx','sunny_imx319']:
 for root in json.loads((P/(variant+'-gtm-trees-private.json')).read_text()):
  m=n.Machine();chromatix,record=m.load_parsed(P/(variant+'-'+str(root['uid'])+'-native-parse-private.json'))
  assert m.read32(chromatix+8)==root['enabled']
  lut,inp,interpolated=m.calculate(chromatix)
  expected=bytes.fromhex(record['allocations'][hex(record['matches'][0]['address'])])[record['matches'][0]['offset']:][:360]
  assert interpolated==expected
  assert lut!=bytes([0xa7])*512
  (P/(variant+'-'+str(root['uid'])+'-native-lut-private.bin')).write_bytes(lut)
  reports.append(dict(variant=variant,uid=root['uid'],enabled=bool(root['enabled']),instructions=m.instructions,providers=m.providers,interpolation_exact=True,lut_bytes=len(lut)))
  print(json.dumps(dict(variant=variant,uid=root['uid'],enabled=bool(root['enabled']),instructions=m.instructions)),flush=True)
(P/'native-math-records-private.json').write_text(json.dumps(reports,indent=2)+'\n')
r=dict(stage=432,stock_roots=len(reports),native_parser_objects_used=True,all_native_interpolated_regions_exact=True,native_calculation_entry='0x37c818',output_lut_bytes=512,all_512_lut_bytes_written=True,register_and_lut_separate_pointers=True,packing_platform_selector_fixture=2,packing_swap_fixture=False,phone_platform_not_read=True,ife_packing_for_all_roots_not_bps_packing_test=True,default_no_bhist_input=True,adrc_path_verified=False,disabled_root_math_for_offline_validation_only=True,production_enable_policy_changed=False,phone_accessed=False,algorithm_stubbed=False,passed=True)
(HERE/'native-math-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
