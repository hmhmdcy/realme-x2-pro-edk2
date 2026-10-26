from pathlib import Path
import importlib.util,hashlib,json,shlex,sys
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;storage.mount.mounted_build()
attempt=sys.argv[1] if len(sys.argv)>1 else 'r1';assert attempt in ['r1','r2','r3']
assert json.loads((HERE/'install-preparation-validation.json').read_text())['passed']
meta=json.loads((P/('install-stage-manifest-private.json' if attempt=='r1' else f'install-stage-manifest-{attempt}-private.json')).read_text());root=meta['phone_root']
proof=json.loads((P/('install-proof-private.json' if attempt=='r1' else f'install-proof-{attempt}-private.json')).read_text())
code=r'''from pathlib import Path
import json
root=Path(ROOT);assert not root.exists()
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
root.mkdir(mode=0o700);print(json.dumps(dict(created=True)))
'''.replace('ROOT',repr(root)).replace('BOOT',repr(proof['boot_id']))
host.ssh('python3 -c '+shlex.quote(code),timeout=20).check_returncode()
s=importlib.util.spec_from_file_location('transport184',HERE.parent/'kernel184/host.py');transport=importlib.util.module_from_spec(s);s.loader.exec_module(transport)
payload=P/('install-payload-private.tar.gz' if attempt=='r1' else f'install-payload-{attempt}-private.tar.gz');assert hashlib.sha256(payload.read_bytes()).hexdigest()==meta['payload_sha256']
q=transport.upload(payload,root+'/payload-private.tar.gz');(P/'install-payload-upload-private.log').write_bytes(q.stdout+q.stderr)
code=r'''from pathlib import Path
import hashlib,json,tarfile,os
root=Path(ROOT);meta=META;assert not (root/'state.json').exists()
assert hashlib.sha256((root/'payload-private.tar.gz').read_bytes()).hexdigest()==meta['payload_sha256']
with tarfile.open(root/'payload-private.tar.gz','r:gz') as tar:
 members=tar.getmembers();assert {m.name for m in members}==set(meta['files_sha256']) and all(m.isfile() for m in members)
 for member in members:
  p=root/member.name;assert p.is_relative_to(root) and '..' not in p.parts
  p.parent.mkdir(parents=True,exist_ok=True)
  with p.open('xb') as f:f.write(tar.extractfile(member).read());f.flush();os.fsync(f.fileno())
for name,digest in meta['files_sha256'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest
for name in ['capture','pipeline-fixture','pipeline-smoke','gst-hardware-probe','pw-hardware-probe']:(root/name).chmod(0o700)
(root/'stage-manifest-private.json').write_text(json.dumps(meta,indent=2)+'\n')
os.sync();print(json.dumps(dict(stage=440,staged=True,forward_and_rollback_cached_and_verified=True,production_modules=3,private_profiles=4,installed=False,passed=True)))
'''.replace('ROOT',repr(root)).replace('META',repr(meta))
q=host.ssh('python3 -c '+shlex.quote(code),timeout=30);q.check_returncode();(HERE/f'install-staging-{attempt}-validation.json').write_bytes(q.stdout);print(q.stdout.decode())
