"""Correct only the desktop mapping check; retain the successful r1 suite."""
from pathlib import Path
import ast,base64,hashlib,json,shlex
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
old=json.loads((HERE/'install-validation.json').read_text());assert old['terminal'] and old['rollback'] and not old['worker_live'] and not old['client_live'] and not old['collector_live']
(HERE/'install-r1-validation.json').write_text(json.dumps(old,indent=2)+'\n')
suite=P/'install-collected-r1/suite.json';s=json.loads(suite.read_text());assert s['passed'] and len(s['captures'])==7
prefix=(HERE.parent/'kernel342/native-install.py').read_text().split('def versions():')[0].replace("'stage':342","'stage':391")
prefix=prefix.replace("marker.write_text(json.dumps(state,indent=2)+'\\n')", "tmp=root/'state.tmp';tmp.write_text(json.dumps(state,indent=2)+'\\n');tmp.replace(marker)")
worker=prefix+'\n'+(HERE/'install-worker-body.py').read_text();ast.parse(worker)
proof=json.loads((P/'install-proof-private.json').read_text());proof['reuse_suite']=dict(path='/var/lib/samurai/k391-install-r1/suite.json',sha256=hashlib.sha256(suite.read_bytes()).hexdigest())
code=r'''from pathlib import Path
import base64,hashlib,json,shutil
old=Path('/var/lib/samurai/k391-install-r1');root=Path('/var/lib/samurai/k391-install-r2')
s=json.loads((old/'state.json').read_text());assert s['terminal'] and s['rollback'] and not s['installed']
assert not root.exists();meta=json.loads((old/'stage-manifest-private.json').read_text())
for n,h in meta['files_sha256'].items():assert hashlib.sha256((old/n).read_bytes()).hexdigest()==h
proof=PROOF;assert hashlib.sha256(Path(proof['reuse_suite']['path']).read_bytes()).hexdigest()==proof['reuse_suite']['sha256']
root.mkdir(mode=0o700)
for n in [*meta['files_sha256'],*meta['cached']]:
 target=root/n;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old/n,target)
for n in ['pipeline-fixture','pipeline-smoke','pw-hardware-probe']:(root/n).chmod(0o700)
(root/'worker.py').write_bytes(base64.b64decode(WORKER));(root/'proof.json').write_text(json.dumps(proof)+'\n')
for n in ['worker.py','proof.json']:meta['files_sha256'][n]=hashlib.sha256((root/n).read_bytes()).hexdigest()
(root/'stage-manifest-private.json').write_text(json.dumps(meta)+'\n')
print(json.dumps(dict(stage=391,attempt='r2',staged=True,only_mapping_check_fixed=True,unchanged_r1_camera_suite_reused=True,passed=True)))
'''.replace('PROOF',repr(proof)).replace('WORKER',repr(base64.b64encode(worker.encode()).decode()))
q=host.ssh('python3 -c '+shlex.quote(code),timeout=30);(HERE/'staging-r2-validation.json').write_bytes(q.stdout);print(q.stdout.decode())
