"""Archive metadata only; no author import/entry, test or device action."""
from pathlib import Path
import hashlib
import json

HERE=Path(__file__).resolve().parent
AUTHOR=HERE.parents[1]/'charging-oem-audit-20261023/irq-cohort-postboot-readonly'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(HERE/'review-result.json')=='aca075eed95122d436f193c3deca182ac81feea10375351986afc642af8b9b7b'
assert sha(AUTHOR/'delivery.json')=='b2c1d2de692b2d302450b0debbfdd50221b84790523829dc57b5c96ba271689b'
old_path=AUTHOR/'history/revision-2-delivery.json'
assert sha(old_path)=='6efc3e39bbef834f1e29926b876e2d8378afce3434c197b3eefc8b4bfddd81a3'
old=json.loads(old_path.read_bytes())
new=json.loads((AUTHOR/'delivery.json').read_bytes())
layout=json.loads((AUTHOR/'archive-layout.json').read_bytes())
assert old['revision']==new['revision']==layout['software_revision']==2
assert new['archive_revision']==layout['archive_revision']==3
assert layout['previous_delivery_stored']=='history/revision-2-delivery.json'
assert layout['previous_delivery_sha256']==new['previous_delivery_sha256']==sha(old_path)
original='history/revision-1/README.md'
stored='history/revision-1/README-original.md.inc'
assert layout['original_path_to_stored_raw']=={original:dict(stored_path=stored,**old['files'][original])}
assert not (AUTHOR/original).exists()
assert sha(AUTHOR/stored)==old['files'][original]['sha256']=='67867ef471593b2fe90cf3c1598ce9939332508dd760a67e560e0f047e0873be'
assert (AUTHOR/stored).stat().st_size==old['files'][original]['bytes']==3893
assert set(new['files'])==set(old['files'])-{original}|{stored,'history/revision-2-delivery.json','archive-layout.json'}
assert len(new['files'])==20
unchanged={}
for n,row in old['files'].items():
    if n in [original,'README.md']:continue
    assert new['files'][n]==row,n
    assert sha(AUTHOR/n)==row['sha256'],n
    unchanged[n]=row['sha256']
for n,row in new['files'].items():
    assert sha(AUTHOR/n)==row['sha256'] and (AUTHOR/n).stat().st_size==row['bytes'],n
# Only one explanatory paragraph was inserted in the top-level README.
lines=(AUTHOR/'README.md').read_bytes().splitlines(keepends=True)
assert lines[2].decode().startswith('归档布局修订3只修历史文档的存放方式')
assert not lines[3].strip()
reconstructed=b''.join(lines[:2]+lines[4:])
assert hashlib.sha256(reconstructed).hexdigest()==old['files']['README.md']['sha256']=='19ee1bc2c2ee2e12e1012292111e4e0c61a3e5e63e4f6056ab7df20803068966'
for key,value in old.items():
    if key!='files':assert new[key]==value,key
result=dict(schema='samurai-irq-cohort-archive-review-v1',status='accepted-archive-layout-only',
 software_revision=2,archive_revision=3,
 original_software_review_sha256=sha(HERE/'review-result.json'),original_review_unchanged=True,
 old_R2_delivery_stored_sha256=sha(old_path),current_delivery_sha256=sha(AUTHOR/'delivery.json'),
 current_file_count=20,raw_original_readme_mapping=layout['original_path_to_stored_raw'],
 raw_original_readme_byte_identical=True,R1_delivery_unchanged=True,
 unchanged_other_R2_files=unchanged,top_readme_only_one_archive_explanation_paragraph_added=True,
 added_files=['history/revision-2-delivery.json','archive-layout.json'],
 runtime_patch_and_all_test_receipts_unchanged=True,
 archive_layout_sha256=sha(AUTHOR/'archive-layout.json'),
 failed_selected_sync_not_replayed_or_modified=True,
 author_files_modified=False,entry_or_tests_or_device_run=False,physical_or_deployment_acceptance=False)
(HERE/'archive-review-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(status=result['status'],archive_review_sha256=sha(HERE/'archive-review-result.json'))))
