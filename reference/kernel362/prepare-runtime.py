"""Reuse361's request probe, replacing the actual core with the rebuilt pipeline."""
from pathlib import Path
import json,shutil
import storage
HERE=Path(__file__).resolve().parent;previous=HERE.parent/'kernel361'
for name in ['build-validation.json','submit-regression-validation.json']:
    assert json.loads((HERE/name).read_text())['passed']
for name in ['adaptation-smoke.cpp','native-probe.py','launch-probe.py','poll-probe.py']:
    content=(previous/name).read_text()
    if name!='adaptation-smoke.cpp':content=content.replace('361','362')
    (HERE/name).write_text(content)
script=(previous/'prepare-runtime.py').read_text().replace('361','362')
needle="cases['wide-optical']=dict(cases[pilot],test_pattern=0)"
assert script.count(needle)==1
script=script.replace(needle,needle+"\nfor name,item in list(cases.items()):\n if name not in ['main-isolated','wide-optical']:cases[name+'-isolated']=dict(item,isolation=True)")
old="prefix/'usr/lib/libcamera.so.0.7.2'"
new="source/'src/libcamera-v0.7.2/output/src/libcamera/libcamera.so.0.7.2'"
assert script.count(old)==2;script=script.replace(old,new)
script=script.replace('packaged_r28_core_and_ipa_used=True','rebuilt362_core_used=True,packaged_r28_ipa_and_proxy_used=True')
script=script.replace('no_isp_or_kernel_source_change=True','camss_submission_serialized=True,no_ipa_or_kernel_source_change=True')
exec(compile(script,str(HERE/'prepare-runtime.py'),'exec'))
