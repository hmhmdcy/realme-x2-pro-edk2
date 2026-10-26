"""Prepare one private completion-ownership candidate; no SDK or phone action."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess
import storage
HERE=Path(__file__).resolve().parent;PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel461')
volume=storage.mount.mounted_build().parent
baseline=volume/'libcamera452-full-ownership';new=storage.candidate()
assert not new.exists(),'Never overwrite an existing candidate'
state=json.loads((HERE.parent/'kernel452/source-state.json').read_text())
proof=json.loads((HERE/'source-draft-validation.json').read_text())
tests=json.loads((HERE/'completion-validation.json').read_text())
assert proof['passed'] and tests['passed']
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
for row in state['source_hashes']:assert sha(baseline/'src/libcamera-v0.7.2'/row['path'])==row['sha256']
usage=sum(p.stat().st_size for p in baseline.rglob('*') if p.is_file() and not p.is_symlink() and not any(s.startswith('pkg') or s=='__pycache__' for s in p.parts))
free=shutil.disk_usage(volume).free
assert free>usage+2*1024**3+256*1024**2,(free,usage)
shutil.copytree(baseline,new,symlinks=True,ignore=lambda directory,names:[n for n in names if n.startswith('pkg') or n=='__pycache__'])
tree=new/'src/libcamera-v0.7.2'
patch=HERE/'0065-camss-retain-request-through-ipa-completion.patch'
for action,extra in [('dry-run',['--dry-run']),('apply',[])]:
 run=subprocess.run(['patch','-p1','--batch','--fuzz=0','-i',str(patch),*extra],cwd=tree,capture_output=True)
 log=run.stdout+run.stderr;(PRIVATE/f'patch-{action}-private.log').write_bytes(log)
 assert run.returncode==0 and b'offset' not in log.lower() and b'fuzz' not in log.lower(),log.decode()
relative='src/libcamera/pipeline/camss-vfe/camss_vfe.cpp'
assert sha(tree/relative)==sha(PRIVATE/'camss_vfe-candidate.cpp')=='befec1da3743545652adc669cc649860d6840738e38a3798305d213b2e874b40'
for row in state['source_hashes']:
 digest=sha(tree/row['path'])
 if row['path']!=relative:assert digest==row['sha256']
 row['sha256']=digest
state.update(stage=461,source=str(tree),baseline_stage=452,changed_this_stage=[relative],
             completion_ownership_fix=True,drop_root_cause_fixed=False,diagnostic_only=False,build_pending=True)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
report=dict(stage=461,free_before_bytes=free,baseline_tree_bytes=usage,free_after_bytes=shutil.disk_usage(volume).free,
 candidate_source_sha256=sha(tree/relative),patch_sha256=sha(patch),only_one_source_changed=True,
 original452_preserved=True,phone_accessed=False,passed=True)
(HERE/'source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
