"""Restore a verified build snapshot after the WSL session terminated."""
from pathlib import Path
import hashlib,importlib.util,json
import host
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py')
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
build=s.mounted_build()
for p in Path('/proc').glob('[0-9]*'):
 try:
  cmd=(p/'cmdline').read_bytes()
  assert not (b'make\0' in cmd and b'camera305' in cmd),'Build still live'
 except (FileNotFoundError,ProcessLookupError):pass
backup=host.PRIVATE/'sensor-build-r4-before-private'
assert backup.is_dir()
expected=json.loads((HERE/'kernel-build-r3-validation.json').read_text())['preserved_build_files_before']
for n in ['Module.symvers','.config']:
 assert hashlib.sha256((backup/n).read_bytes()).hexdigest()==expected[n]
restored=[]
for p in backup.rglob('*'):
 if p.is_file():
  target=build/p.relative_to(backup)
  if not target.exists() or target.read_bytes()!=p.read_bytes():
   target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(p.read_bytes());restored.append(str(p.relative_to(backup)))
actual={n:hashlib.sha256((build/n).read_bytes()).hexdigest() for n in expected}
assert actual==expected
report=dict(stage=305,interrupted_attempt=4,matching_live_make_process=False,
 verified_snapshot_restored=True,restored_build_files=restored,image_dtb_symvers_config_unchanged=True,
 no_device_mutation=True)
(HERE/'build-interruption-recovery-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
