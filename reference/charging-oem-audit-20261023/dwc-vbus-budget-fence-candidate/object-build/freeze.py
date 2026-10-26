"""Read/hash the completed eight-object supplement; no volume/device access."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
LEAF=HERE.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(LEAF/'delivery.json')=='8d7a963a3aef17a16ef5e8ec19d96b31de4f066b261e315d28727c6d0b1e16aa'
source_delivery=json.loads((LEAF/'delivery.json').read_bytes())
for name,row in source_delivery['files'].items():assert sha(LEAF/name)==row['sha256'],name
r=json.loads((HERE/'build-result.json').read_bytes())
assert r['passed'] and r['parent_error'] is None and len(r['phases'])==8
assert r['inputs_before']==r['inputs_after'] and r['tracked_source502_shared_inputs_unchanged']
assert r['parent_mounts_unchanged_after_original_helper']
assert r['copied_sources']==source_delivery['candidate']
assert r['source_delivery_sha256']==sha(LEAF/'delivery.json')
assert r['files']['build-eight.py']==sha(HERE/'build-eight.py')
assert all(p['terminal'] is True and p['returncode']==0 and not p['diagnostic_lines'] and p['aarch64_relocatable'] for p in r['phases'])
assert all(r[k] is True for k in ['no_make','no_link','no_Image','no_module','software_budget_only'])
assert not r['device_SSH_USB_SDK_Git_used']
owner=json.loads((HERE/'owner-result.json').read_bytes())
assert owner['terminal'] and owner['returncode']==0
assert owner['original_compiler_pids']==[p['pid'] for p in r['phases']]
files=['derive.py','derivation-result.json','build-eight.py','build-result.json','owner-result.json','freeze.py']
result=dict(schema='samurai-dwc-vbus-budget-fence-source-and-build-supplement-v1',passed=True,
    files={n:dict(sha256=sha(HERE/n),bytes=(HERE/n).stat().st_size) for n in files},
    source_delivery=dict(path='../delivery.json',sha256=sha(LEAF/'delivery.json')),
    BUILD_document=dict(path='../BUILD.md',sha256=sha(LEAF/'BUILD.md')),
    copied_sources=r['copied_sources'],actual_original502_base=True,
    original_config_sha256='23e088a90736bbbc442c672d82b35c11bf04f7dc489f1c6afb1b03dc0d8f30ed',
    all_eight_core_h_consumers_compiled_W1_Werror=True,
    objects={p['target']:dict(sha256=p['object_sha256'],bytes=p['object_bytes'],pid=p['pid'],returncode=p['returncode']) for p in r['phases']},
    original_host_handle=52441,original_host_handle_terminal_returncode=0,
    tracked_inputs_unchanged=True,helper_post_mountinfo_unchanged=True,window_returned=True,
    Image_module_or_carrier_linked=False,device_SSH_USB_SDK_Git_used=False,
    runtime_or_direct_complete_or_PM_hardware_accepted=False,
    archive=dict(explicit_source_text_json_whitelist=files+['../BUILD.md'],recursive_scan=False,object_or_raw_log_in_public_leaf=False))
(HERE/'delivery.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(dict(passed=True,delivery_sha256=sha(HERE/'delivery.json'),build_result_sha256=sha(HERE/'build-result.json'),source_delivery_sha256=sha(LEAF/'delivery.json'))))
