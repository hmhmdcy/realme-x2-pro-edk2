from pathlib import Path
import ast,hashlib,importlib.util,json,shlex,tarfile
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;root='/var/lib/samurai/k392-runtime-r1'
assert json.loads((HERE/'client-build-validation.json').read_text())['passed']
prefix=(HERE.parent/'kernel342/native-install.py').read_text().split('def versions():')[0].replace("'stage':342","'stage':392")
prefix=prefix.replace("marker.write_text(json.dumps(state,indent=2)+'\\n')", "tmp=root/'state.tmp';tmp.write_text(json.dumps(state,indent=2)+'\\n');tmp.replace(marker)")
worker=prefix+'\n'+(HERE/'worker-body.py').read_text();ast.parse(worker);(P/'worker.py').write_text(worker)
collector=(HERE.parent/'kernel391/dump-collector.py').read_text().replace('start<600','start<180').replace('start>=600','start>=180');(P/'dump-collector.py').write_text(collector)
files={n:P/n for n in ['worker.py','dump-collector.py','cancel-client']};proof=json.loads((P.parent/'kernel391/install-proof-private.json').read_text())
meta=dict(stage=392,sha256={n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in files.items()},camss_note_sha256=proof['camss_note_sha256'])
(P/'manifest.json').write_text(json.dumps(meta)+'\n');files['manifest.json']=P/'manifest.json'
payload=P/'runtime-payload-private.tar.gz';assert not payload.exists()
with tarfile.open(payload,'w:gz') as t:
 for n,p in files.items():t.add(p,arcname=n,recursive=False)
code=r'''from pathlib import Path
import json
root=Path(ROOT);assert not root.exists()
dev=Path('/sys/bus/platform/devices/ac10000.icp');s=json.loads((dev/'m2m_status').read_text());assert not any(s[k] for k in ['users','running','fatal','pinned','orphans'])
root.mkdir(mode=0o700);print(json.dumps(dict(staging_created=True,before=s)))
'''.replace('ROOT',repr(root))
q=host.ssh('python3 -c '+shlex.quote(code),timeout=20);(P/'preflight-private.json').write_bytes(q.stdout)
spec=importlib.util.spec_from_file_location('transport184',HERE.parent/'kernel184/host.py');transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
q=transport.upload(payload,root+'/payload-private.tar.gz');(P/'upload-private.log').write_bytes(q.stdout+q.stderr)
code=r'''from pathlib import Path
import hashlib,json,tarfile
root=Path(ROOT);sha=SHA
assert hashlib.sha256((root/'payload-private.tar.gz').read_bytes()).hexdigest()==sha
with tarfile.open(root/'payload-private.tar.gz','r:gz') as t:
 members=t.getmembers();assert {m.name for m in members}=={'manifest.json','worker.py','dump-collector.py','cancel-client'} and all(m.isfile() for m in members)
 for m in members:
  with (root/m.name).open('xb') as f:f.write(t.extractfile(m).read())
(root/'cancel-client').chmod(0o700)
meta=json.loads((root/'manifest.json').read_text())
for n,h in meta['sha256'].items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h
print(json.dumps(dict(stage=392,staged=True,kernel_modules_packages_and_profiles_unchanged=True,passed=True)))
'''.replace('ROOT',repr(root)).replace('SHA',repr(hashlib.sha256(payload.read_bytes()).hexdigest()))
q=host.ssh('python3 -c '+shlex.quote(code),timeout=25);(HERE/'staging-validation.json').write_bytes(q.stdout);print(q.stdout.decode())
