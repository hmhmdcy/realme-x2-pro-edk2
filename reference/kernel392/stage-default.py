from pathlib import Path
import ast,base64,hashlib,json,shlex
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
r=json.loads((HERE/'runtime-r2-validation.json').read_text());assert r['state']['passed'] and not any(r[k] for k in ['worker_live','client_live','collector_live'])
prefix=(HERE.parent/'kernel342/native-install.py').read_text().split('def versions():')[0].replace("'stage':342","'stage':392")
prefix=prefix.replace("marker.write_text(json.dumps(state,indent=2)+'\\n')", "tmp=root/'state.tmp';tmp.write_text(json.dumps(state,indent=2)+'\\n');tmp.replace(marker)")
worker=prefix+'\n'+(HERE/'default-worker-body.py').read_text();ast.parse(worker)
fixture=P.parent/'kernel363/pipeline-fixture';collector=P/'dump-collector.py'
meta=dict(stage=392,sha256={'worker.py':hashlib.sha256(worker.encode()).hexdigest(),'pipeline-fixture':hashlib.sha256(fixture.read_bytes()).hexdigest(),'dump-collector.py':hashlib.sha256(collector.read_bytes()).hexdigest()})
code=r'''from pathlib import Path
import base64,hashlib,json,shutil
root=Path('/var/lib/samurai/k392-runtime-r3');assert not root.exists();root.mkdir(mode=0o700)
shutil.copyfile('/var/lib/samurai/k391-install-r2/pipeline-fixture',root/'pipeline-fixture');(root/'pipeline-fixture').chmod(0o700)
shutil.copyfile('/var/lib/samurai/k392-runtime-r2/dump-collector.py',root/'dump-collector.py')
(root/'worker.py').write_bytes(base64.b64decode(WORKER));meta=META
for n,h in meta['sha256'].items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h
(root/'manifest.json').write_text(json.dumps(meta)+'\n');print(json.dumps(dict(stage=392,attempt='r3',default_installed_application_recovery_staged=True,passed=True)))
'''.replace('WORKER',repr(base64.b64encode(worker.encode()).decode())).replace('META',repr(meta))
q=host.ssh('python3 -c '+shlex.quote(code),timeout=20);(HERE/'staging-r3-validation.json').write_bytes(q.stdout);print(q.stdout.decode())
