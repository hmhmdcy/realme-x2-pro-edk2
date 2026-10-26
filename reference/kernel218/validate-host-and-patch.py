from pathlib import Path
import hashlib,json,subprocess

here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel218')
root=Path('/home/cy122/x2pro-linux/libcamera214-root');original=root/'work/libcamera/src/libcamera-v0.7.2';src=root/'work/libcamera218'
test=json.loads((private/'native-quad-host-test.log').read_text().strip());assert test['passed']
linked=subprocess.check_output(['readelf','-d',str(private/'native-quad-test-asan')],text=True)
assert 'libasan.so' in linked and 'libubsan.so' in linked
proof=json.loads((here/'candidate-source-validation.json').read_text())
assert all(hashlib.sha256((src/name).read_bytes()).hexdigest()==digest for name,digest in proof['files'].items())
different=[]
for path in src.rglob('*'):
    if not path.is_file() or 'output' in path.relative_to(src).parts:continue
    name=str(path.relative_to(src))
    if not (original/name).is_file() or path.read_bytes()!=(original/name).read_bytes():different.append(name)
assert sorted(different)==sorted(proof['files'])
patch=(here/'libcamera-native-quad-candidate.patch').read_bytes()
p=subprocess.run(['patch','--dry-run','--batch','-p1','-d',str(original)],input=patch,capture_output=True)
(private/'patch-dry-run-private.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0
report=dict(stage=218,algorithm_test=test,host_address_and_undefined_sanitizers_linked=True,
            candidate_patch_dry_run_passed=True,isolated_source_difference_count=len(different),
            only_declared_candidate_files_differ=True,production214_source_unmodified=True,
            candidate_patch_sha256=hashlib.sha256(patch).hexdigest())
(here/'host-source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
