"""Verify original IFE command order, bank sequencing and full LUT payload."""
from pathlib import Path
import importlib.util,json,struct
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
module('storage433transport',HERE.parent/'kernel284/storage.py').mounted_build();n=module('native433transport',HERE/'gtm-transport-model.py')
variant='sunny_s5kgw1';old=P.parent/'kernel432';selected=next(s for tag,c,s in json.loads((P.parent/'kernel431'/(variant+'-gtm-selections-private.json')).read_text()) if tag=='gtm10_ife' and c[2]==0)
m=n.Machine();chromatix,_=m.load_parsed(old/(variant+'-'+str(selected['uid'])+'-native-parse-private.json'));m.create(chromatix);records=[]
for i,step in enumerate([0,1,2]):
 adrc=(old/(variant+'-'+str(step)+'-adrc-private.bin')).read_bytes();result=m.execute(adrc,lux=[140.,210.,280.][i]);assert not result['result'] and result['calculations']==1
 assert len(result['register_writes'])==1 and result['register_writes'][0]==(0x794,struct.pack('<I',i&1))
 assert len(result['dmi'])==1;dmi=result['dmi'][0];assert dmi['selector']==24+(i&1) and dmi['offset']==56 and dmi['payload']==(old/(variant+'-'+str(step)+'-adrc-lut-private.bin')).read_bytes()
 assert result['calculated_enable']==0xa6a6a6a4 and result['next_selector']==24+((i+1)&1) and result['next_bank']==((i+1)&1)
 result['register_writes']=[(hex(a),b.hex()) for a,b in result['register_writes']];result['dmi'][0]['payload']=dmi['payload'].hex();records.append(result)
held=m.execute(adrc,force=False,lux=280.);assert held['result']==0 and held['calculations']==0 and not held['register_writes'] and not held['dmi']
locked=m.execute(adrc,force=True,lux=281.,locks=(1,1));assert locked['result']==0 and locked['calculations']==0 and not locked['register_writes'] and not locked['dmi']
m.fail_dmi=True;failed=m.execute(adrc,force=True,lux=282.);assert failed['result']==1 and failed['calculations']==1 and len(failed['dmi'])==1 and failed['next_selector']==24 and failed['next_bank']==0 and failed['calculated_enable']==0xa6a6a6a0
failed['register_writes']=[(hex(a),b.hex()) for a,b in failed['register_writes']];failed['dmi'][0]['payload']=failed['dmi'][0]['payload'].hex()
front='sunny_imx471';front_selected=next(s for tag,c,s in json.loads((P.parent/'kernel431'/(front+'-gtm-selections-private.json')).read_text()) if tag=='gtm10_ife' and c[2]==0)
fm=n.Machine();fc,_=fm.load_parsed(old/(front+'-'+str(front_selected['uid'])+'-native-parse-private.json'));fm.create(fc);disabled=fm.execute(bytes(4240));assert disabled['result']==0 and disabled['calculations']==0 and not disabled['register_writes'] and not disabled['dmi'] and disabled['calculated_enable']==0xa6a6a6a0
(P/'transport-records-private.json').write_text(json.dumps(dict(sequence=records,held=held,locked=locked,failed=failed,disabled_front=disabled,providers=m.providers,instructions=m.instructions),indent=2)+'\n')
r=dict(stage=433,original_create_entry='0x31f7f0',original_execute_entry='0x31fc00',complete_original_execute_calls=7,calculated_successful_requests=3,held_requests=1,locked_requests=1,disabled_front_requests=1,injected_dmi_transport_failure_requests=1,native_failure_toggles_next_bank_but_does_not_publish_enable=True,gtm_register_offset='0x794',dmi_config_offset='0xc24',dmi_selectors=[24,25,24],lut_bytes=512,dmi_buffer_offset_bytes=56,all_complete_successful_luts_equal_original_math=True,calculated_color_enable_bit=2,unrelated_color_bits_preserved=True,next_bank_toggles_after_write=True,selected_module_fixture_from_original_parser=True,original_mode_manager_not_rerun=True,transport_recorded_not_sent_to_hardware=True,platform_state_explicit_fixture=True,phone_accessed=False,passed=True)
(HERE/'transport-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
