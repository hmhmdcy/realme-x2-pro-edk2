from pathlib import Path
import ast,base64,hashlib,importlib.util,json,shlex,sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;attempt=sys.argv[1] if len(sys.argv)>1 else 'r2';assert attempt in ['r2','r3','r4'];previous='r'+str(int(attempt[1:])-1)
old=json.loads((HERE/'runtime-validation.json').read_text());assert old['state']['terminal'] and not old['state']['installed'] and not any(old[k] for k in ['worker_live','client_live','collector_live'])
(HERE/('runtime-'+previous+'-validation.json')).write_text(json.dumps(old,indent=2)+'\n')
if attempt=='r2':assert json.loads((HERE/'r1-recovery-validation.json').read_text())['passed']
else:assert old['state']['rollback']
prefix=(HERE.parent/'kernel342/native-install.py').read_text().split('def versions():')[0].replace("'stage':342","'stage':393")
prefix=prefix.replace("marker.write_text(json.dumps(state,indent=2)+'\\n')", "tmp=root/'state.tmp';tmp.write_text(json.dumps(state,indent=2)+'\\n');tmp.replace(marker)")
worker=prefix+'\n'+(HERE/'deploy-worker-body.py').read_text();ast.parse(worker);(P/('worker-'+attempt+'.py')).write_text(worker)
code=r'''from pathlib import Path
import base64,hashlib,json,shutil
old=Path('/var/lib/samurai/k393-deployment-'+PREVIOUS);root=old.with_name('k393-deployment-'+ATTEMPT);assert not root.exists()
assert json.loads((old/('recovery-state.json' if PREVIOUS=='r1' else 'state.json')).read_text()).get('passed') or json.loads((old/'state.json').read_text()).get('rollback')
meta=json.loads((old/'manifest.json').read_text())
for r in meta['modules']:
 assert hashlib.sha256(Path(r['target']).read_bytes()).hexdigest()==r['old_sha256']
 assert hashlib.sha256(Path('/sys/module',r['module'],'notes/.note.gnu.build-id').read_bytes()).hexdigest()==r['old_note_sha256']
root.mkdir(mode=0o700)
for n,h in meta['payload_sha256'].items():
 assert hashlib.sha256((old/n).read_bytes()).hexdigest()==h
 shutil.copyfile(old/n,root/n)
(root/'worker.py').write_bytes(base64.b64decode(WORKER));meta['payload_sha256']['worker.py']=hashlib.sha256((root/'worker.py').read_bytes()).hexdigest()
for n in ['local-error-client','pipeline-fixture']:(root/n).chmod(0o700)
(root/'manifest.json').write_text(json.dumps(meta)+'\n');print(json.dumps(dict(current_client_sha256=meta['payload_sha256']['local-error-client'])))
'''.replace('WORKER',repr(base64.b64encode(worker.encode()).decode())).replace('PREVIOUS',repr(previous)).replace('ATTEMPT',repr(attempt))
q=host.ssh('python3 -c '+shlex.quote(code),timeout=25)
client=P/'local-error-client';digest=hashlib.sha256(client.read_bytes()).hexdigest();root='/var/lib/samurai/k393-deployment-'+attempt
if json.loads(q.stdout)['current_client_sha256']!=digest:
 spec=importlib.util.spec_from_file_location('transport184',HERE.parent/'kernel184/host.py');transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
 q=transport.upload(client,root+'/local-error-client');(P/('upload-'+attempt+'-private.log')).write_bytes(q.stdout+q.stderr)
code=r'''from pathlib import Path
import hashlib,json
root=Path(ROOT);meta=json.loads((root/'manifest.json').read_text());assert hashlib.sha256((root/'local-error-client').read_bytes()).hexdigest()==SHA
meta['payload_sha256']['local-error-client']=SHA;(root/'local-error-client').chmod(0o700)
for n,h in meta['payload_sha256'].items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h
(root/'manifest.json').write_text(json.dumps(meta)+'\n');print(json.dumps(dict(stage=393,attempt=ATTEMPT,old_pair_recovery_verified=True,staged=True,passed=True)))
'''.replace('ROOT',repr(root)).replace('SHA',repr(digest)).replace('ATTEMPT',repr(attempt))
q=host.ssh('python3 -c '+shlex.quote(code),timeout=25);(HERE/('staging-'+attempt+'-validation.json')).write_bytes(q.stdout);print(q.stdout.decode())
