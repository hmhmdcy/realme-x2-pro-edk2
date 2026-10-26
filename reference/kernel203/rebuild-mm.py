"""Rebuild the already validated191 source in its original isolated native SDK."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys

os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k203-mm-rebuild';assert not out.exists();out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k203-baseline/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#183 ') and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
base=root/'k190-mm-build';sdk=root/'k190-mm-sdk';source=next((base/'source').iterdir())/'src/mm-shared-qmi.c'
assert hashlib.sha256(source.read_bytes()).hexdigest()=='949132f3203b78300224a1fb958cbd1fa44202661f35f64dbed4f84f3ff5ed24'
original_candidate=root/'k191-mm-build/candidate/ModemManager';expected='b350c55ba334b7d23564136fe3ce19bf37f95db0d374f63cc89351341d9b9ddc'
assert hashlib.sha256(original_candidate.read_bytes()).hexdigest()==expected and hashlib.sha256(Path('/usr/bin/ModemManager').read_bytes()).hexdigest()==expected
db=Path('/lib/apk/db/installed').read_bytes();env=json.loads((base/'build-environment-private.json').read_text())
for name,args in [('clean-private-build-output',[str(sdk/'usr/bin/ninja'),'-C',str(base/'build'),'-t','clean','src/ModemManager']),('compile',[str(sdk/'usr/bin/ninja'),'-C',str(base/'build'),'-j2','src/ModemManager'])]:
 with (out/(name+'-private.log')).open('wb') as log:subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=1200,env=env)
candidate=out/'ModemManager';shutil.copyfile(base/'build/src/ModemManager',candidate);candidate.chmod(0o755)
raw=hashlib.sha256(candidate.read_bytes()).hexdigest()
sys.path.insert(0,str(sdk/'usr/lib/python3.14/site-packages'))
from mesonbuild.scripts.depfixer import Elf,DT_RPATH,DT_RUNPATH
with Elf(str(candidate),verbose=False) as elf:
 for tag in [DT_RPATH,DT_RUNPATH]:
  if any(entry.d_tag==tag for entry in elf.dynamic):elf.remove_rpath_entry(tag)
digest=hashlib.sha256(candidate.read_bytes()).hexdigest()
assert db==Path('/lib/apk/db/installed').read_bytes() and hashlib.sha256(Path('/usr/bin/ModemManager').read_bytes()).hexdigest()==expected
r=dict(stage=203,clean_recompiled_from_pinned191_source=True,raw_candidate_sha256=raw,candidate_sha256=digest,byte_identical_to_validated191=digest==expected,installed_mm_and_package_database_unchanged=True,build_sdk_190_reused=True,installed_binary_not_replaced=True)
(out/'summary.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));assert digest==expected,'Rebuilt binary differs: inspect before packaging or deployment'
