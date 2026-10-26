from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
os.umask(0o077)
out=Path('/var/lib/samurai/k190-mm-build');sdk=Path('/var/lib/samurai/k190-mm-sdk')
report=json.loads((out/'build-validation.json').read_text())
original=out/'build/src/ModemManager';assert hashlib.sha256(original.read_bytes()).hexdigest()==report['candidate_sha256']
destination=out/'candidate';destination.mkdir(mode=0o700)
binary=destination/'ModemManager';shutil.copyfile(original,binary);binary.chmod(0o755)
sys.path.insert(0,str(sdk/'usr/lib/python3.14/site-packages'))
from mesonbuild.scripts.depfixer import Elf,DT_RPATH,DT_RUNPATH
with Elf(str(binary),verbose=False) as elf:
 for tag in [DT_RPATH,DT_RUNPATH]:
  if any(entry.d_tag==tag for entry in elf.dynamic):elf.remove_rpath_entry(tag)
env=dict(os.environ);env.pop('LD_LIBRARY_PATH',None);env.pop('LD_PRELOAD',None)
elf=subprocess.run([str(sdk/'usr/bin/readelf'),'-h','-d',str(binary)],capture_output=True,check=True,env=dict(env,LD_LIBRARY_PATH=str(sdk/'usr/lib'))).stdout.decode()
assert 'AArch64' in elf and '(RUNPATH)' not in elf and '(RPATH)' not in elf
(out/'candidate-final-elf-private.txt').write_text(elf)
deps=subprocess.run(['ldd',str(binary)],capture_output=True,check=True,env=env)
(out/'candidate-final-ldd-private.txt').write_bytes(deps.stdout+deps.stderr)
assert b'not found' not in deps.stdout+deps.stderr and b'Error' not in deps.stdout+deps.stderr
assert os.fsencode(out) not in deps.stdout+deps.stderr and os.fsencode(sdk) not in deps.stdout+deps.stderr
version=subprocess.run([str(binary),'--version'],capture_output=True,check=True,env=env)
(out/'candidate-version-private.txt').write_bytes(version.stdout+version.stderr)
assert b'1.25.95' in version.stdout
report.update(deployable_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),build_rpath_removed=True,system_runtime_libraries_resolved=True,version_works_with_system_libraries=True)
(out/'candidate-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
