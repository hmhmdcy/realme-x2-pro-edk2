"""Export only this release and commit it locally, preserving unrelated work."""
from pathlib import Path
import ast,hashlib,importlib.util,json,subprocess,textwrap
import host,storage
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=host.PRIVATE;storage.mount.mounted_build()
repo=Path('/home/cy122/edk2-samurai/repo');prefix=Path('Platform/Realme/sm8150');mirror=repo/prefix
def git(*args):return subprocess.check_output(['git','-C',str(repo),*args])
assert git('rev-parse','HEAD').decode().strip()=='01a71e6fd9ac33b0f91539354f540b39213eafc3'
assert json.loads((HERE/'current-state-validation.json').read_text())['installed']
spec=importlib.util.spec_from_file_location('docs',ROOT/'linux-port/scripts/docs-health-check.py');docs=importlib.util.module_from_spec(spec);spec.loader.exec_module(docs);exporter=docs.public_module(ROOT)
fixed=['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md','sessions/INDEX.md','archive/NEXT-SESSION-through439-2026-10-22.md','linux-port/camera/README.md','linux-port/camera/kernel/README.md','linux-port/docs/HARDWARE-STATUS.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']
files=[Path(x) for x in fixed]
for directory in [HERE,ROOT/'linux-port/packages/libcamera',ROOT/'linux-port/packages/samurai-camera-config']:
 files.extend(p.relative_to(ROOT) for p in directory.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
files=sorted(set(files));assert all(p.suffix in ['.py','.json','.md','.patch','.cpp','.yaml','.desktop','.rules','.conf'] or p.name=='APKBUILD' for p in files)
paths=[(prefix/p).as_posix() for p in files];scope=set(paths)
def outside_index(raw):return [r for r in raw.split(b'\0') if r and r.split(b'\t',1)[1].decode() not in scope]
def outside_status(raw):
 rows=raw.split(b'\0');result=[];i=0
 while i<len(rows):
  row=rows[i];i+=1
  if not row:continue
  path=row[3:].decode();record=[row]
  if b'R' in row[:2] or b'C' in row[:2]:record.append(rows[i]);i+=1
  if path not in scope:result.extend(record)
 return result
before_index=git('ls-files','-s','-z');before_status=git('status','--porcelain=v1','-z','--untracked-files=all')
(P/'mirror-before-index-private.bin').write_bytes(before_index);(P/'mirror-before-status-private.bin').write_bytes(before_status)
unrelated={}
for row in outside_status(before_status):
 if row[:2]!=b'??' and len(row)>3:
  p=repo/row[3:].decode()
  if p.is_file():unrelated[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
errors=[]
for rel in files:
 if rel.suffix=='.md' and rel.as_posix()!='archive/NEXT-SESSION-through439-2026-10-22.md':errors+=docs.link_errors(ROOT,rel)
 if rel.suffix=='.py':ast.parse(textwrap.dedent((ROOT/rel).read_text()),filename=str(rel))
 if rel.suffix=='.json':json.loads((ROOT/rel).read_text())
assert not errors,errors
for rel in files:
 target=mirror/rel;assert target.is_relative_to(mirror) and not target.is_symlink()
 target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(exporter.public_bytes(ROOT,rel))
for rel in files:assert (mirror/rel).read_bytes()==exporter.public_bytes(ROOT,rel)
git('add','--',*paths)
assert outside_index(git('ls-files','-s','-z'))==outside_index(before_index)
assert outside_status(git('status','--porcelain=v1','-z','--untracked-files=all'))==outside_status(before_status)
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==digest for p,digest in unrelated.items())
message=P/'commit-message.txt';message.write_text('''camera: deploy stock automatic IQ for four cameras

Ship the signed r32/r27 cohort with matched production modules and private factory profiles. Bind real same-frame PD10 and effective GTM/WB versions to successful IPA tone history, preserving front IPE colour and stock switches. Require PD10 only when a processed consumer exists so RAW-only requests configure correctly.

Validation:406 native/isolated images across four cameras,386 math commits;90 RAW-only and6dual images;default GStreamer/RAW/automatic IQ/PipeWire paths and offline rollback. Current installed epoch56direct,zero faults or taint. Further processed dimensions,video/HDR and optical/multicamera calibration remain open.
''')
commit=subprocess.run(['git','-C',str(repo),'commit','--only','-F',str(message),'--',*paths],capture_output=True,text=True);(P/'local-commit-private.log').write_text(commit.stdout+commit.stderr);assert commit.returncode==0,commit.stderr
head=git('rev-parse','HEAD').decode().strip()
assert outside_index(git('ls-files','-s','-z'))==outside_index(before_index)
assert outside_status(git('status','--porcelain=v1','-z','--untracked-files=all'))==outside_status(before_status)
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==digest for p,digest in unrelated.items())
actual=set(git('diff-tree','--no-commit-id','--name-only','-r',head).decode().splitlines());assert actual and actual<=scope
report=dict(stage=440,local_commit=head,exported_files=len(files),committed_files=len(actual),unrelated_index_and_status_preserved=True,unrelated_tracked_worktree_hashes_preserved=True,public_export_used=True,private_coefficients_pixels_not_exported=True,pushed=False,installed=True,full_goal_complete=False,passed=True)
(P/'local-mirror-validation-private.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
