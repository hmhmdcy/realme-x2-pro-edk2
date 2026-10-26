"""Freeze an offline source-only revision; does not invoke firmware or hardware."""
from pathlib import Path
import hashlib
import json

HERE=Path(__file__).resolve().parent
R1=HERE.parent/'eud-boot-policy'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
tested=json.loads((HERE/'test-result.json').read_bytes());candidate=json.loads((HERE/'candidate-result.json').read_bytes())
assert tested['passed'] and candidate['passed'] and tested['case_count']==5
for name,digest in tested['files'].items():assert sha((HERE/name).read_bytes())==digest,name
old=json.loads((R1/'result.json').read_bytes())
for name,digest in old['files'].items():assert sha((R1/name).read_bytes())==digest,name
files={p.name:sha(p.read_bytes()) for p in sorted(HERE.iterdir()) if p.is_file() and p.name not in ['result.json','test-r2']}
result={'passed':True,'status':'frozen offline R2 for independent review','revision':2,'files':files,
    'candidate_source_sha256':candidate['candidate_source_sha256'],'full_patch_sha256':files['boot-policy.patch'],'r1_delta_sha256':files['r1-to-r2.patch'],
    'known_full_words':[0,1,0x01010101],'literal_only_no_low_byte_mask':True,'write_target_full_word':0,
    'native_candidate_sha256':candidate['native_candidate_sha256'],'DTB_reused_without_regeneration':True,
    'all_other_R1_bytes_unchanged':True,'affected_actual_helper_case_count':5,'R1_12_cases_rerun':False,'independent_FDT_review_rerun':False,
    'R1_files_unchanged':True,'R8_source_package_modified':False,'full_firmware_built':False,'Image_built':False,'SDK_invoked':False,
    'device_accessed':False,'ssh_executed':False,'usb_accessed':False,'shared_tree_modified':False,'Git_index_modified':False,
    'hardware_write_executed':False,'hardware_CSR_zero_proven':False,'USB500_causality_proven':False,'deployed':False}
(HERE/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'passed':True,'result_sha256':sha((HERE/'result.json').read_bytes()),'candidate_source_sha256':result['candidate_source_sha256'],'full_patch_sha256':result['full_patch_sha256'],'r1_delta_sha256':result['r1_delta_sha256']}))
