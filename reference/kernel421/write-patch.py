"""Reproduce only this candidate's authored source delta from420."""
from pathlib import Path
import difflib,hashlib,json,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;tree=storage.candidate()/'src/libcamera-v0.7.2';base=tree.parents[2]/'libcamera420-request-r31/src/libcamera-v0.7.2'
s=json.loads((HERE/'source-state.json').read_text());patch=''
for item in s['source_hashes']:
 name=item['path'];assert hashlib.sha256((tree/name).read_bytes()).hexdigest()==item['sha256']
 a=(base/name).read_text() if (base/name).exists() else '';b=(tree/name).read_text()
 patch+=''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='a/'+name if a else '/dev/null',tofile='b/'+name))
p=HERE/'0042-camss-ipe-frame-history.patch';p.write_text(patch)
check=host.PRIVATE/'patch-check';assert not check.exists();check.mkdir()
for item in s['source_hashes']:
 name=item['path'];src=base/name
 if src.exists():dest=check/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(src.read_bytes())
q=subprocess.run(['patch','--batch','--fuzz=0','-p1','-i',str(p)],cwd=check,capture_output=True);(host.PRIVATE/'patch-apply.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stdout.decode()[-1000:]
for item in s['source_hashes']:assert (check/item['path']).read_bytes()==(tree/item['path']).read_bytes()
r=dict(stage=421,files=4,zero_fuzz_reproduces_actual_candidate=True,base_stage=420,passed=True)
(HERE/'source-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
