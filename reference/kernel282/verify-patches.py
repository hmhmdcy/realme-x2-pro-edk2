"""Reconstruct both committed trees in private temporary indexes, without a checkout."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import host

ROOT=Path(__file__).resolve().parent
TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
records=[]
for name,parent,commit in [
    ('multistream-prerequisites.patch','21facb9a7941ecd0a624a9e4fccd9ae544dde7b5','2985ef200e4ae28d567f5919a4d8657ac0559b65'),
    ('vfe175-output-candidate.patch','2985ef200e4ae28d567f5919a4d8657ac0559b65','18b48939788bc7f95fb2999ea986846a67f0c62c')]:
    index=host.PRIVATE/(name+'.reproduction-index-private')
    assert not index.exists()
    env=dict(os.environ,GIT_INDEX_FILE=str(index))
    run=lambda *args:subprocess.check_output(['git','-C',str(TREE),*args],env=env,text=True).strip()
    run('read-tree',parent)
    run('apply','--cached','--check',str(ROOT/name))
    run('apply','--cached',str(ROOT/name))
    actual=run('write-tree');expected=run('rev-parse',commit+'^{tree}')
    assert actual==expected
    index.unlink()
    records.append(dict(patch=name,parent=parent,commit=commit,exact_tree=actual,
                        sha256=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()))
assert not subprocess.check_output(['git','-C',str(TREE),'status','--porcelain'],text=True)
(ROOT/'patch-reproduction-validation.json').write_text(json.dumps(dict(stage=282,
    real_index_and_worktree_unchanged=True,reproductions=records),indent=2)+'\n')
print(json.dumps(records,indent=2))
