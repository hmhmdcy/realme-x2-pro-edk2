"""Use the existing scoped close check for the new completed transaction."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent
state=json.loads((HERE/'source-state.json').read_text());state.update(stage=400,maintained_source_stage=399,source_unchanged_from399=True,temporary_adapter_source_restored=True);(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
text=(HERE.parent/'kernel397/close-current.py').read_text().replace('stage=397','stage=400').replace('k397-colour-r1','k400-chain-r1').replace('parameters/test_cc_mode','parameters/test_chain_mode')
text=text.replace("assert not Path('/sys/module/camss_icp_a5_m2m/parameters/test_chain_mode').exists()", "assert not Path('/sys/module/camss_icp_a5_m2m/parameters/test_cc_mode').exists()\nassert not Path('/sys/module/camss_icp_a5_m2m/parameters/test_chain_mode').exists()")
text=text.replace('hardware_fixed_diagonal_cc_effect_verified=True','hardware_colour_chain_fixed_modes_verified=True,hardware_nv12_nv21_equivalence_verified=True,off_diagonal_and_signed_offset_effect_verified=True,rgb_domain_proof_limited_to_tested_pair=True')
(HERE/'close-current.py').write_text(text)
(HERE/'preparation-validation.json').write_text(json.dumps(dict(stage=400,initial_client_build_failed=True,initial_client_failure='Werror misleading indentation for adjacent if statements',client_failure_log_retained_private=True,fixture_token_collision_corrected_before_adapter_build=True,initial_fixture_retained_private=True,adapter_build_attempts=1,adapter_build_passed=True,only_core_and_adapter_loaded_standard_helpers_not_installed=True,normal_core399_reused_byte_identical_to_test_core=True,passed=True),indent=2)+'\n')
print('Prepared scoped restored-device check; historical first client compile failure retained.')
