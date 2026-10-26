"""Freeze only the reviewed source and targeted saved-function evidence."""
from pathlib import Path
import ast,hashlib,json
HERE=Path(__file__).resolve().parent
sha=lambda raw:hashlib.sha256(raw).hexdigest()

def main():
    test=json.loads((HERE/'test-result.json').read_bytes())
    assert test['passed'] is True and test['actual_function_groups']==11 and test['saved_parser_and_codec_cases']==18
    assert test['original_inputs_unchanged'] is True and test['old_suites_rerun'] is False and test['module_or_Image_built'] is False
    assert test['actual_function_run']['terminal'] is True and test['actual_function_run']['returncode']==0
    assert all(row['terminal'] is True and row['returncode']==0 for row in test['build_commands'])
    for name,digest in test['source_files'].items():assert sha((HERE/name).read_bytes())==digest,name
    base=json.loads((HERE/'source-base.json').read_bytes())
    for name,digest in base['source_base'].items():assert sha((HERE.parent/'protection-query-observer-candidate'/name).read_bytes())==digest
    assert len(test['unchanged_production_functions'])==11
    files=['gauge-protocol.h','gauge-i2c.h','samurai-gauge-protection.c','parse-saved-profile.py','frame-decoder-profile.c',
        'prepare.py','profile.patch','source-base.json','test-profile.c','run-tests.py','test-result.json','execution-receipt.json','README.md','freeze.py']
    for name in files:
        if name.endswith('.py'):ast.parse((HERE/name).read_bytes())
    value={'schema':'samurai-observed-2719-diagnostic-profile-source-v1','passed':True,'frozen':True,
      'files':{name:{'sha256':sha((HERE/name).read_bytes()),'bytes':len((HERE/name).read_bytes())} for name in files},
      'actual_function_groups':11,'saved_parser_codec_cases':18,'default_profile':'standard',
      'load_only_parameter':'observed_2719_diagnostic=1;0444','profile1_requires_fresh_complete0001_2719':True,
      'cache_schema':2,'legacy_schema1_attempt_cannot_be_relabelled':True,
      'original_normal_Health_six_command_and_wire_functions_identical':11,
      'original_real_attempt_size4_error_minus90_after0A_missing_preserved':True,
      'candidate_success_batch_after0A_simulated_only':True,'old_suites_rerun':False,
      'compatibility_or_new_bits_TCA_safety_accepted':False,'module_Image_or_new_query_created':False,'device_accessed':False}
    raw=(json.dumps(value,indent=2)+'\n').encode()
    with (HERE/'delivery.json').open('xb') as stream:stream.write(raw)
    print(json.dumps({'passed':True,'delivery_sha256':sha(raw)}))

if __name__=='__main__':main()
