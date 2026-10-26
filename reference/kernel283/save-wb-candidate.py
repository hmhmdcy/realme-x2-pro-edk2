"""Commit the verified staged candidate using an isolated index; do not checkout."""
from pathlib import Path
import hashlib
import json
import os
import subprocess

ROOT=Path(__file__).resolve().parent
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel283')
TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
BASE='18b48939788bc7f95fb2999ea986846a67f0c62c'
BRANCH='samurai-vfe175-wb283'
BUILD=json.loads((ROOT/'wb-overlay-build-validation.json').read_text())
assert BUILD['exit']==0 and len(BUILD['objects'])==33
assert json.loads((ROOT/'wb-host-tests-validation.json').read_text())['actual_initial_queue_helpers_tested']
assert subprocess.check_output(['git','-C',str(TREE),'rev-parse','HEAD'],text=True).strip()==BASE
assert not subprocess.check_output(['git','-C',str(TREE),'status','--porcelain'],text=True)
assert subprocess.run(['git','-C',str(TREE),'show-ref','--verify','--quiet','refs/heads/'+BRANCH]).returncode==1
index=PRIVATE/'wb-commit-index-private'
assert not index.exists()
env=dict(os.environ,GIT_INDEX_FILE=str(index),
         GIT_AUTHOR_NAME='Samurai Builder',GIT_AUTHOR_EMAIL='samurai@localhost',
         GIT_COMMITTER_NAME='Samurai Builder',GIT_COMMITTER_EMAIL='samurai@localhost')
def git(*args,input=None):
    return subprocess.check_output(['git','-C',str(TREE),*args],env=env,input=input).decode().strip()
git('read-tree',BASE)
prefix='drivers/media/platform/qcom/camss/'
files={prefix+n:PRIVATE/'wb-candidate'/n for n in
       ['Makefile','camss-vfe-175-pixel.c','camss-vfe-175-pixel.h','camss-vfe-17x.c','camss-vfe.c','camss-vfe.h']}
files['include/uapi/linux/qcom-camss-config.h']=PRIVATE/'wb-uapi/linux/qcom-camss-config.h'
for name,path in files.items():
    blob=git('hash-object','-w','--stdin',input=path.read_bytes())
    git('update-index','--add','--cacheinfo','100644',blob,name)
tree=git('write-tree')
patch=subprocess.check_output(['git','-C',str(TREE),'diff','--cached','--binary','--full-index',BASE],env=env)
assert len(patch)>1000
(ROOT/'vfe175-wb-candidate.patch').write_bytes(patch)
check=subprocess.run(['perl',str(TREE/'scripts/checkpatch.pl'),'--no-tree',str(ROOT/'vfe175-wb-candidate.patch')],text=True,capture_output=True)
(PRIVATE/'wb-checkpatch-private.txt').write_text(check.stdout+check.stderr)
assert '0 errors' in check.stdout,check.stdout
message=b'''media: qcom: camss: add VFE175 white balance parameter backend

Translate existing U15Q10 typed WB parameters to the matched U12Q7 VFE175
registers. Preserve reserved fields, use neutral gain for bypass, cache
updates while disabled, and reject unsupported offsets and padding.

Reuse the common initial parameter queue in 17x before output starts and
size IFE metadata buffers for the WB payload. Keep the current three RDI
resources unchanged; the complete pixel processing chain remains pending.

Signed-off-by: Samurai Builder <samurai@localhost>
'''
commit=git('commit-tree',tree,'-p',BASE,input=message)
git('update-ref','refs/heads/'+BRANCH,commit,'0'*40)
assert not subprocess.check_output(['git','-C',str(TREE),'status','--porcelain'],text=True)
assert subprocess.check_output(['git','-C',str(TREE),'rev-parse','HEAD'],text=True).strip()==BASE
# Independently reproduce the candidate tree by applying its saved patch.
verify=PRIVATE/'wb-verify-index-private';assert not verify.exists()
env_verify=dict(env,GIT_INDEX_FILE=str(verify))
for args in [['read-tree',BASE],['apply','--cached','--check',str(ROOT/'vfe175-wb-candidate.patch')],
             ['apply','--cached',str(ROOT/'vfe175-wb-candidate.patch')]]:
    subprocess.run(['git','-C',str(TREE),*args],env=env_verify,check=True,capture_output=True)
reproduced=subprocess.check_output(['git','-C',str(TREE),'write-tree'],env=env_verify,text=True).strip()
assert reproduced==tree
report=dict(stage=283,commit=commit,branch=BRANCH,parent=BASE,tree=tree,
            reproduced_tree=reproduced,isolated_index=True,original_checkout_still_clean_at_parent=True,
            source_sha256={n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in files.items()},
            patch_sha256=hashlib.sha256(patch).hexdigest(),checkpatch_exit=check.returncode,
            checkpatch_summary=[l for l in check.stdout.splitlines() if l.startswith('total:')],
            not_checked_out=True,not_pushed=True,not_deployed=True)
(ROOT/'candidate-commit-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
