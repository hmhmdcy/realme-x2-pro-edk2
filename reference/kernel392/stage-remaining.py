from pathlib import Path
import ast,base64,hashlib,importlib.util,json,shlex
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;root='/var/lib/samurai/k392-runtime-r2'
previous=json.loads((HERE/'runtime-r1-validation.json').read_text());assert not any(previous[k] for k in ['worker_live','client_live','collector_live'])
assert previous['state']['terminal'] and [c['case'] for c in previous['state']['cases']]==[0,1,2]
prefix=(HERE.parent/'kernel342/native-install.py').read_text().split('def versions():')[0].replace("'stage':342","'stage':392")
prefix=prefix.replace("marker.write_text(json.dumps(state,indent=2)+'\\n')", "tmp=root/'state.tmp';tmp.write_text(json.dumps(state,indent=2)+'\\n');tmp.replace(marker)")
worker=prefix+'\n'+(HERE/'worker-body.py').read_text();ast.parse(worker)
meta=json.loads((P/'manifest.json').read_text());meta.update(expected_cases=2,expected_cancellations=1,client_args=['--remaining'])
meta['sha256']['cancel-client']=hashlib.sha256((P/'cancel-client').read_bytes()).hexdigest();meta['sha256']['worker.py']=hashlib.sha256(worker.encode()).hexdigest()
code=r'''from pathlib import Path
import json,shutil
root=Path(ROOT);old=root.with_name('k392-runtime-r1');s=json.loads((old/'state.json').read_text());assert s['terminal']
assert not root.exists();root.mkdir(mode=0o700);shutil.copyfile(old/'dump-collector.py',root/'dump-collector.py');print('Created remaining-case staging root')
'''.replace('ROOT',repr(root))
host.ssh('python3 -c '+shlex.quote(code),timeout=20)
spec=importlib.util.spec_from_file_location('transport184',HERE.parent/'kernel184/host.py');transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
q=transport.upload(P/'cancel-client',root+'/cancel-client');(P/'upload-r2-private.log').write_bytes(q.stdout+q.stderr)
code=r'''from pathlib import Path
import base64,hashlib,json
root=Path(ROOT);(root/'worker.py').write_bytes(base64.b64decode(WORKER));meta=META
(root/'cancel-client').chmod(0o700)
for n,h in meta['sha256'].items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h
(root/'manifest.json').write_text(json.dumps(meta)+'\n');print(json.dumps(dict(stage=392,attempt='r2',already_passed_first_three_cases_not_rerun=True,peer_pattern_and_crc_prepared_before_active_work=True,staged=True,passed=True)))
'''.replace('ROOT',repr(root)).replace('WORKER',repr(base64.b64encode(worker.encode()).decode())).replace('META',repr(meta))
q=host.ssh('python3 -c '+shlex.quote(code),timeout=20);(HERE/'staging-r2-validation.json').write_bytes(q.stdout);print(q.stdout.decode())
