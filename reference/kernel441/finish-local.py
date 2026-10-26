"""Incrementally export this candidate and handoff without staging or pushing."""
from pathlib import Path
import json,subprocess
import host
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=host.PRIVATE
repo=Path('/home/cy122/edk2-samurai/repo');prefix=Path('Platform/Realme/sm8150')
files=[Path(n) for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','linux-port/camera/README.md','linux-port/docs/HARDWARE-STATUS.md']]
files+=sorted(p.relative_to(ROOT) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
assert all((ROOT/p).is_file() and not (ROOT/p).is_symlink() for p in files)
scope={(prefix/p).as_posix() for p in files}
def git(*args):return subprocess.check_output(['git','-C',str(repo),*args])
def outside_status(raw):
 rows=raw.split(b'\0');result=[];i=0
 while i<len(rows):
  row=rows[i];i+=1
  if not row:continue
  record=[row]
  if b'R' in row[:2] or b'C' in row[:2]:record.append(rows[i]);i+=1
  if row[3:].decode() not in scope:result.extend(record)
 return result
before_index=git('ls-files','-s','-z');before_status=git('status','--porcelain=v1','-z','--untracked-files=all')
q=subprocess.run(['bash',str(ROOT/'linux-port/scripts/sync-docs-to-repo.sh'),'--files',*[p.as_posix() for p in files]],capture_output=True)
(P/'scoped-public-export-private.log').write_bytes(q.stdout+q.stderr)
assert not q.returncode,(q.stdout+q.stderr).decode()[-5000:]
assert before_index==git('ls-files','-s','-z')
assert outside_status(before_status)==outside_status(git('status','--porcelain=v1','-z','--untracked-files=all'))
r=dict(stage=441,files=len(files),scoped_public_export_and_links_checked=True,git_index_unchanged=True,unrelated_status_preserved=True,pushed=False,candidate_installed=False,candidate_release_ready=False,passed=True)
(P/'local-mirror-validation-private.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
