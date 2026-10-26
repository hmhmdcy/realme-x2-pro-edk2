from pathlib import Path
import hashlib,importlib.util,json,shlex
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;meta=json.loads((P/'stage-manifest-private.json').read_text());root='/var/lib/samurai/k391-install-r1'
meta['cached']['pw-hardware-probe'].setdefault('sha256',hashlib.sha256((storage.SDK/'private/camss316-runtime/pw-hardware-probe').read_bytes()).hexdigest())
code=r'''from pathlib import Path
import hashlib,json
root=Path(ROOT);assert not root.exists();cached=CACHED
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k390-active/boot-id-private.txt').read_bytes()
for n,r in cached.items():assert hashlib.sha256(Path(r['path']).read_bytes()).hexdigest()==r['sha256'],n
root.mkdir(mode=0o700);print('Verified cached rollback/probes and created391 staging root.')
'''.replace('ROOT',repr(root)).replace('CACHED',repr(meta['cached']))
print(host.ssh('python3 -c '+shlex.quote(code),timeout=25).stdout.decode())
spec=importlib.util.spec_from_file_location('transport184',HERE.parent/'kernel184/host.py');transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
payload=P/'install-payload-private.tar.gz';assert hashlib.sha256(payload.read_bytes()).hexdigest()==meta['payload_sha256']
q=transport.upload(payload,root+'/payload-private.tar.gz');(P/'payload-upload-private.log').write_bytes(q.stdout+q.stderr)
code=r'''from pathlib import Path
import hashlib,json,os,shutil,tarfile
root=Path(ROOT);meta=META;assert not (root/'state.json').exists()
assert hashlib.sha256((root/'payload-private.tar.gz').read_bytes()).hexdigest()==meta['payload_sha256']
with tarfile.open(root/'payload-private.tar.gz','r:gz') as tar:
 members=tar.getmembers();assert {m.name for m in members}==set(meta['files_sha256']) and all(m.isfile() for m in members)
 for m in members:
  target=root/m.name;target.parent.mkdir(parents=True,exist_ok=True)
  with target.open('xb') as f:f.write(tar.extractfile(m).read());f.flush();os.fsync(f.fileno())
for n,digest in meta['files_sha256'].items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==digest
for n,r in meta['cached'].items():
 target=root/n;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(r['path'],target);assert hashlib.sha256(target.read_bytes()).hexdigest()==r['sha256']
for n in ['pipeline-fixture','pipeline-smoke','pw-hardware-probe']:(root/n).chmod(0o700)
(root/'stage-manifest-private.json').write_text(json.dumps(meta)+'\n')
print(json.dumps(dict(stage=391,staged=True,new_packages_installed=False,rollback_cached_and_verified=True,passed=True)))
'''.replace('ROOT',repr(root)).replace('META',repr(meta))
q=host.ssh('python3 -c '+shlex.quote(code),timeout=30);(HERE/'staging-validation.json').write_bytes(q.stdout);print(q.stdout.decode())
