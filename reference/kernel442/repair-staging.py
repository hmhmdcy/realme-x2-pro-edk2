"""Finish the verified, never-launched r1 staging after a chmod-list typo."""
from pathlib import Path
import hashlib,json,shlex
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
storage.mount.mounted_build()
files={'worker.py':P/'runtime-worker.py','baseline-private.json':P/'preflight-private.json','pipeline-fixture':P.parent/'kernel363/pipeline-fixture','factory-s5kgw1-private.yaml':P.parent/'kernel440/factory-s5kgw1-private.yaml','capture':P/'capture','proof.json':P/'runtime-proof-private.json'}
for name,row in json.loads((P/'runtime-input-files-private.json').read_text()).items():files[name]=Path(row['path'])
for row in json.loads((HERE/'intree-build-validation.json').read_text())['modules']:
 if row['runtime_candidate']:files[row['name']+'.ko']=Path(row['private_path'])
expected={n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in files.items()}
code='''from pathlib import Path
import hashlib,json,os
r=Path('/var/lib/samurai/k442-callback-timing-r1')
assert not any((r/n).exists() for n in ['state.json','launch.json','worker.log'])
m=json.loads((r/'manifest.json').read_text());assert m==EXPECTED
for n,h in m.items():assert hashlib.sha256((r/n).read_bytes()).hexdigest()==h
for n in ['capture','pipeline-fixture','proxy/camss_ipa_proxy']:(r/n).chmod(0o700)
for n in ['libcamera','libcamera-base']:
 p=r/f'lib/{n}.so.0.7';target=f'{n}.so.0.7.2'
 if p.is_symlink():assert os.readlink(p)==target
 else:assert not p.exists();p.symlink_to(target)
print(json.dumps(dict(stage=442,staged=True,root=str(r),recovered_never_launched_staging=True,passed=True)))
'''.replace('EXPECTED',repr(expected))
q=host.ssh('python3 -c '+shlex.quote(code),timeout=25);q.check_returncode();(HERE/'runtime-staging-r1-validation.json').write_bytes(q.stdout);print(q.stdout.decode())
