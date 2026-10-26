"""Resume the verified completed prefix copy after a temporary-directory clash."""
from pathlib import Path
import hashlib,json,os,stat
here=Path(__file__).resolve().parent;sdk=Path('/home/cy122/x2pro-linux/libcamera214-root');private=Path('/mnt/e/edk2-samurai-out/kernel224')
prefix=Path('/home/cy122/x2pro-linux/libcamera224-r10-qa-prefix');dest=sdk/'candidate224-r10'
assert dest.is_dir() and not (sdk/'tmp/k224-r10-runtime').exists()
def inventory(root):
 result={}
 for p in root.rglob('*'):
  if p.is_symlink():result[str(p.relative_to(root))]=dict(target=os.readlink(p))
  elif p.is_file():result[str(p.relative_to(root))]=dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),mode=stat.S_IMODE(p.stat().st_mode))
 return result
assert inventory(prefix)==inventory(dest)
script=(here/'host-r10-runtime-qa.py').read_text()
old='assert not destination.exists();shutil.copytree(prefix,destination,symlinks=True)';assert script.count(old)==1
script=script.replace(old,'assert destination.is_dir()').replace("root/'tmp/k224-runtime'","root/'tmp/k224-r10-runtime'")
script=script.replace("label+'-host-runtime-private.log'","label+'-r10-host-runtime-private.log'").replace("path.name+'-embedded-key-verify-private.log'","path.name+'-r10-embedded-key-verify-private.log'")
compile(script,'r10-runtime-qa-resumed','exec');exec(compile(script,str(here/'host-r10-runtime-qa.py'),'exec'))
r=dict(stage=224,host_qa_setup_failure='r9 and r10 initially shared tmp/k224-runtime',verified_existing_r10_prefix_copy_before_resume=True,separate_r10_runtime_directory_used=True,first_failed_setup_did_not_run_runtime_tests=True)
(here/'r10-host-qa-setup-correction-validation.json').write_text(json.dumps(r,indent=2)+'\n')
