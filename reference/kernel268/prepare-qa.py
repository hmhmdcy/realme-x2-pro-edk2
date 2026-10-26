"""Preserve the existing full-feature/signature/runtime QA against the new packages."""
from pathlib import Path
import json

R=Path(__file__).resolve().parent
assert json.loads((R/'r19-package-build-validation.json').read_text())['package_count']==13
for name in ['inspect-full-features.py','collect-forward-packages.py','host-runtime-qa.py']:
    s=(R.parent/'kernel239'/name).read_text().replace('kernel239','kernel268').replace('239-r15','268-r19').replace('r15','r19').replace('stage=239','stage=268').replace('k239','k268').replace('0.1.0-r10','0.1.0-r14')
    compile(s,name,'exec');(R/name).write_text(s)
# Correct the historical cache label without discarding the original build receipt.
p=R/'r19-package-build-validation.json';d=json.loads(p.read_text())
d['r15_cache_files_unchanged']=d.pop('r14_cache_files_unchanged')
d['actual_cache_source']='libcamera239-r15-built'
p.write_text(json.dumps(d,indent=2)+'\n')
print('Prepared full-feature and signed ARM runtime QA for r19/r14.')
