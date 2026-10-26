"""Close quoted header dependencies of the selected CAMSS implementation."""
from pathlib import Path
import difflib,hashlib,json,os,re,shutil
import host
HERE=Path(__file__).resolve().parent;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
INLINE=SDK/'work/libcamera299-inline';BASE=SDK/'work/libcamera278-r24-r3-built/src/libcamera-v0.7.2'
report_path=HERE/'package-source-validation.json';report=json.loads(report_path.read_text())
selected=set(report['changed_source_sha256']);seen=set();pending=list(selected);added=[]
patch=HERE/'0029-camss-hardware-pipeline.patch';text=patch.read_text()
while pending:
 name=pending.pop()
 if name in seen:continue
 seen.add(name);p=INLINE/name
 if not p.is_file():continue
 for header in re.findall(r'^#include\s+"([^"]+)"',p.read_text(),re.M):
  local=Path(os.path.normpath(str(Path(name).parent/header)))
  include=local if (INLINE/local).is_file() else Path('include')/header
  if not (INLINE/include).is_file():continue
  rel=include.as_posix();pending.append(rel)
  if rel in selected:continue
  before=(BASE/include).read_text() if (BASE/include).exists() else ''
  after=(INLINE/include).read_text()
  if before==after:continue
  selected.add(rel);added.append(rel)
  text+=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+rel if before else '/dev/null',tofile='b/'+rel))
  report['changed_source_sha256'][rel]=hashlib.sha256(after.encode()).hexdigest()
  target=SDK/'work/libcamera316-r25-built/src/libcamera-v0.7.2'/include
  target.parent.mkdir(parents=True,exist_ok=True);target.write_text(after)
patch.write_text(text)
for recipe in [HERE/'recipes/libcamera',SDK/'work/libcamera316-r25']:
 shutil.copyfile(patch,recipe/patch.name)
 p=recipe/'APKBUILD';lines=p.read_text().splitlines(True)
 for i,line in enumerate(lines):
  if line.endswith('  '+patch.name+'\n'):lines[i]=hashlib.sha512(patch.read_bytes()).hexdigest()+'  '+patch.name+'\n'
 p.write_text(''.join(lines))
report['quoted_source_dependencies_added']=added;report_path.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'added_dependencies':added}))
