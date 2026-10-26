from pathlib import Path
import ast,hashlib,importlib.util,json,shlex
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;preflight=json.loads((HERE/'preflight-validation.json').read_text());assert preflight['passed']
private=json.loads((P/'preflight-private.json').read_text());baseline=json.loads((P.parent/'kernel388/sg-runtime-baseline-private.json').read_text())
proof=dict(guard='/var/lib/samurai/k378-recovered/boot-id-private.txt',module_root=private['module_root'],modules=private['modules'],camss_note_sha256=baseline['qcom_camss']['note_sha256'],sg_note_sha256=baseline['videobuf2_dma_sg']['note_sha256'])
prefix=(HERE.parent/'kernel342/native-install.py').read_text().split('def versions():')[0].replace("'stage':342","'stage':390")
source=prefix+'\n'+(HERE/'module-worker-body.py').read_text();ast.parse(source);(P/'module-worker.py').write_text(source)
code="""from pathlib import Path
import json,os
root=Path('/var/lib/samurai/k390-deployment');assert not root.exists()
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path(GUARD).read_bytes()
root.mkdir(mode=0o700);(root/'boot-id-private.txt').write_bytes(Path('/proc/sys/kernel/random/boot_id').read_bytes());(root/'proof.json').write_text(PROOF)
print('Created390 private staging directory.')
""".replace('GUARD',repr(proof['guard'])).replace('PROOF',repr(json.dumps(proof)))
print(host.ssh('python3 -c '+shlex.quote(code),timeout=20).stdout.decode())
spec=importlib.util.spec_from_file_location('transport184',HERE.parent/'kernel184/host.py');transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
payload=P.parent/'kernel389/modules-firmware-private.tar.gz';expected=json.loads((HERE.parent/'kernel389/deployment-package-validation.json').read_text())['separate_modules_firmware_sha256'];assert hashlib.sha256(payload.read_bytes()).hexdigest()==expected
q=transport.upload(payload,'/var/lib/samurai/k390-deployment/payload-private.tar.gz');(P/'upload-private.log').write_bytes(q.stdout+q.stderr)
q=transport.upload(P/'module-worker.py','/var/lib/samurai/k390-deployment/worker.py');(P/'upload-worker-private.log').write_bytes(q.stdout+q.stderr)
manifest=json.loads((P.parent/'kernel389/module-stage-manifest-private.json').read_text())
code=r'''from pathlib import Path
import hashlib,tarfile,json,os
root=Path('/var/lib/samurai/k390-deployment');assert not (root/'state.json').exists()
assert hashlib.sha256((root/'payload-private.tar.gz').read_bytes()).hexdigest()==DIGEST
names=NAMES
with tarfile.open(root/'payload-private.tar.gz','r:gz') as tar:
 members=tar.getmembers();assert {m.name for m in members}==names and all(m.isfile() for m in members)
 for m in members:
  target=root/m.name;target.parent.mkdir(parents=True,mode=0o700,exist_ok=True)
  with target.open('xb') as f:f.write(tar.extractfile(m).read());f.flush();os.fsync(f.fileno())
manifest=json.loads((root/'manifest.json').read_text())
for name,digest in manifest['files_sha256'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest
assert hashlib.sha256((root/'worker.py').read_bytes()).hexdigest()==WORKER
print(json.dumps(dict(stage=390,staged=True,module_files_not_changed=True,passed=True)))
'''.replace('DIGEST',repr(expected)).replace('NAMES',repr(set(manifest['files_sha256'])|{'manifest.json'})).replace('WORKER',repr(hashlib.sha256(source.encode()).hexdigest()))
q=host.ssh('python3 -c '+shlex.quote(code),timeout=25);(HERE/'staging-validation.json').write_bytes(q.stdout);print(q.stdout.decode())
