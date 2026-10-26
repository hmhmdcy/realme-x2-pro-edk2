"""Finalize the handoff in the unpublished local release commit."""
from pathlib import Path
import importlib.util,json,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=host.PRIVATE;storage.mount.mounted_build()
record=P/'local-mirror-validation-private.json';d=json.loads(record.read_text());repo=Path('/home/cy122/edk2-samurai/repo');prefix=Path('Platform/Realme/sm8150')
def git(*args):return subprocess.check_output(['git','-C',str(repo),*args])
assert git('rev-parse','HEAD').decode().strip()==d['local_commit'] and not d['pushed']
p=HERE/'IN-PROGRESS.json';state=json.loads(p.read_text());state.update(phase='release-installed-verified-and-locally-committed',local_public_export_complete=True,local_commit_receipt='E:/edk2-samurai-out/kernel440/local-mirror-validation-private.json');state['next']=state['next'][1:];p.write_text(json.dumps(state,indent=2)+'\n')
rel=p.relative_to(ROOT);target=prefix/rel;scope={target.as_posix(),(prefix/Path(__file__).resolve().relative_to(ROOT)).as_posix()}
before=git('ls-files','-s','-z')
def other(raw):return [x for x in raw.split(b'\0') if x and x.split(b'\t',1)[1].decode() not in scope]
spec=importlib.util.spec_from_file_location('docs',ROOT/'linux-port/scripts/docs-health-check.py');docs=importlib.util.module_from_spec(spec);spec.loader.exec_module(docs);exporter=docs.public_module(ROOT)
for r in [rel,Path(__file__).resolve().relative_to(ROOT)]:
 (repo/prefix/r).write_bytes(exporter.public_bytes(ROOT,r))
git('add','--',*sorted(scope));assert other(git('ls-files','-s','-z'))==other(before)
q=subprocess.run(['git','-C',str(repo),'commit','--amend','--only','--no-edit','--',*sorted(scope)],capture_output=True,text=True);(P/'local-amend-private.log').write_text(q.stdout+q.stderr);assert q.returncode==0,q.stderr
assert other(git('ls-files','-s','-z'))==other(before)
d.update(previous_unpublished_commit=d['local_commit'],local_commit=git('rev-parse','HEAD').decode().strip(),handoff_export_finalized=True,exported_files=d['exported_files']+1,committed_files=len(git('diff-tree','--no-commit-id','--name-only','-r','HEAD').decode().splitlines()))
record.write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
