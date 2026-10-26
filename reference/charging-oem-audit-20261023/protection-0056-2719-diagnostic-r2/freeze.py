"""Freeze the saved-only diagnostic result. No runtime/query interface."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
sha=lambda raw:hashlib.sha256(raw).hexdigest()

def create(path,value):
    with path.open('xb') as stream:stream.write((json.dumps(value,indent=2)+'\n').encode())

def main():
    tests=json.loads((HERE/'test-result.json').read_bytes())
    assert tests['passed'] is True and tests['new_cases']==10 and tests['original_inputs_unchanged'] is True
    for name,digest in tests['source_files'].items():assert sha((HERE/name).read_bytes())==digest
    execution=json.loads((HERE/'execution-receipt.json').read_bytes())
    assert execution['passed'] is True and execution['targeted_test']['exit_code']==execution['default_check']['exit_code']==0
    private=Path(tests['private_output']); original=private/'analysis-r2-private.json'
    raw=original.read_bytes(); result=json.loads(raw)
    assert result['observed_frame_valid'] is True and result['observed_payload_bytes']==3 and result['original_validate_rc']==-90
    assert result['raw_value_u24']==596048 and result['original_batch_stage']==4 and result['original_batch_error']==-90
    assert result['batch_sequence_complete'] is result['stability_verified'] is result['compatibility_verified'] is False
    assert result['source_authentication_newly_verified'] is result['battery_after_read'] is False
    assert sha((private/'frame-decoder-r2').read_bytes())==tests['diagnostic_decoder_sha256']
    public={key:value for key,value in result.items() if key!='raw_payload_hex'}
    public['private_analysis']={'path':str(original),'sha256':sha(raw)}
    public['test_cases']=10; public['new_queries']=0; public['new_modules']=0
    create(HERE/'result.json',public)
    files=['frame-decoder-r2.c','analyze-saved.py','test-saved.py','test-result.json','source-evidence.json',
           'execution-receipt.json','README.md','result.json','freeze.py']
    delivery={'schema':'samurai-2719-0056-diagnostic-addendum-r2','passed':True,'frozen':True,
       'files':{name:{'sha256':sha((HERE/name).read_bytes()),'bytes':len((HERE/name).read_bytes())} for name in files},
       'actual_C_validator_reused':tests['actual_C_header_sha256'],'diagnostic_decoder_sha256':tests['diagnostic_decoder_sha256'],
       'new_targeted_cases':10,'original_provider_and_runtime_size4_EMSGSIZE_preserved':True,
       'TI_standard_fourth_reserved_byte_conflict_preserved':True,'old_suites_rerun':False,
       'device_accessed':False,'query_rearm_reload_or_module_created':False,'compatibility_TCA_stability_accepted':False}
    create(HERE/'delivery.json',delivery)
    print(json.dumps({'passed':True,'delivery_sha256':sha((HERE/'delivery.json').read_bytes()),'result_sha256':sha((HERE/'result.json').read_bytes())}))

if __name__=='__main__':main()
