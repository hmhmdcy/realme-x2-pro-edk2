from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
os.umask(0o077)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k189r2-reboot-runtime/boot-id-private.txt').read_bytes()
out=Path('/var/lib/samurai/k191-mm-build');previous=Path('/var/lib/samurai/k190-mm-build');sdk=Path('/var/lib/samurai/k190-mm-sdk')
source=next((previous/'source').iterdir())/'src/mm-shared-qmi.c'
before=source.read_bytes();assert hashlib.sha256(before).hexdigest()=='a9e6c2765e07683bf84e1876d5ecb1cba64e71db25cbe561816c56ff4efabdfa'
patched=(out/'mm-shared-qmi-patched.c').read_bytes();assert hashlib.sha256(patched).hexdigest()=='949132f3203b78300224a1fb958cbd1fa44202661f35f64dbed4f84f3ff5ed24'
(out/'mm-shared-qmi-before-private.c').write_bytes(before)
old_binary=previous/'build/src/ModemManager';assert hashlib.sha256(old_binary.read_bytes()).hexdigest()=='ff0416e08ef74181c1face4ebf29ed947d9981492f5644e944aa4508d9fccf58'
shutil.copyfile(old_binary,out/'ModemManager-build-before-private')
db=Path('/lib/apk/db/installed').read_bytes();source.write_bytes(patched)
env=json.loads((previous/'build-environment-private.json').read_text())
with (out/'compile-private.log').open('wb') as log:
 subprocess.run([str(sdk/'usr/bin/ninja'),'-C',str(previous/'build'),'-j2','src/ModemManager'],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=1200,env=env)
assert source.read_bytes()==patched and Path('/lib/apk/db/installed').read_bytes()==db
candidate_dir=out/'candidate';candidate_dir.mkdir(mode=0o700);candidate=candidate_dir/'ModemManager'
shutil.copyfile(old_binary,candidate);candidate.chmod(0o755)
raw_sha=hashlib.sha256(candidate.read_bytes()).hexdigest()
sys.path.insert(0,str(sdk/'usr/lib/python3.14/site-packages'))
from mesonbuild.scripts.depfixer import Elf,DT_RPATH,DT_RUNPATH
with Elf(str(candidate),verbose=False) as elf:
 for tag in [DT_RPATH,DT_RUNPATH]:
  if any(entry.d_tag==tag for entry in elf.dynamic):elf.remove_rpath_entry(tag)
clean_env=dict(os.environ);clean_env.pop('LD_LIBRARY_PATH',None);clean_env.pop('LD_PRELOAD',None)
elf=subprocess.run([str(sdk/'usr/bin/readelf'),'-h','-d',str(candidate)],capture_output=True,check=True,env=dict(clean_env,LD_LIBRARY_PATH=str(sdk/'usr/lib'))).stdout.decode()
assert 'AArch64' in elf and '(RUNPATH)' not in elf and '(RPATH)' not in elf;(out/'candidate-elf-private.txt').write_text(elf)
ldd=subprocess.run(['ldd',str(candidate)],capture_output=True,check=True,env=clean_env);(out/'candidate-ldd-private.txt').write_bytes(ldd.stdout+ldd.stderr)
assert all(x not in ldd.stdout+ldd.stderr for x in [b'not found',b'Error',os.fsencode(sdk),os.fsencode(previous)])
version=subprocess.run([str(candidate),'--version'],capture_output=True,check=True,env=clean_env);assert b'1.25.95' in version.stdout
(out/'candidate-version-private.txt').write_bytes(version.stdout+version.stderr)
report=dict(stage=191,source_sha256=hashlib.sha256(patched).hexdigest(),raw_candidate_sha256=raw_sha,candidate_sha256=hashlib.sha256(candidate.read_bytes()).hexdigest(),
 compiled_aarch64=True,system_runtime_libraries_resolved=True,build_rpath_removed=True,version_with_system_libraries=True,package_database_unchanged=True,
 reused_signed190_sdk=True,reused190_incremental_build=True,previous_source_and_raw_binary_backed_up=True)
(out/'build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
