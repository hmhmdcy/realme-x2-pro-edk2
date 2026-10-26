"""Carry the299 kernel-sequence and metadata FourCC integration into r25."""
from pathlib import Path
import difflib,hashlib,json,shutil
import host
HERE=Path(__file__).resolve().parent;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
INLINE=SDK/'work/libcamera299-inline';BASE=SDK/'work/libcamera278-r24-r3-built/src/libcamera-v0.7.2'
patch=HERE/'0029-camss-hardware-pipeline.patch';text=patch.read_text()
report_path=HERE/'package-source-validation.json';report=json.loads(report_path.read_text())
for relative in ['src/libcamera/v4l2_videodevice.cpp','include/linux/videodev2.h']:
 old=(BASE/relative).read_text();new=(INLINE/relative).read_text()
 assert '+++ b/'+relative+'\n' not in text
 text+=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+relative,tofile='b/'+relative))
 target=SDK/'work/libcamera316-r25-built/src/libcamera-v0.7.2'/relative
 assert target.read_text()==old;target.write_text(new)
 report['changed_source_sha256'][relative]=hashlib.sha256(new.encode()).hexdigest()
patch.write_text(text)
for recipe in [HERE/'recipes/libcamera',SDK/'work/libcamera316-r25']:
 shutil.copyfile(patch,recipe/patch.name)
 p=recipe/'APKBUILD';lines=p.read_text().splitlines(True)
 for i,line in enumerate(lines):
  if line.endswith('  '+patch.name+'\n'):lines[i]=hashlib.sha512(patch.read_bytes()).hexdigest()+'  '+patch.name+'\n'
 p.write_text(''.join(lines))
report_path.write_text(json.dumps(report,indent=2)+'\n')
print('Included299 shared frame identity assignment and metadata FourCC definitions.')
