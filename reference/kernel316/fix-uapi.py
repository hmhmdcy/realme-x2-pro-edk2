"""Add the already used generic ISP ABI header to the complete package patch."""
from pathlib import Path
import difflib,hashlib,json,shutil
import host
HERE=Path(__file__).resolve().parent;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
relative='include/linux/media/v4l2-isp.h'
old=SDK/'work/libcamera278-r24-r3-built/src/libcamera-v0.7.2'/relative
new=SDK/'work/libcamera299-inline'/relative
patch=HERE/'0029-camss-hardware-pipeline.patch'
shutil.copyfile(patch,host.PRIVATE/'0029-before-uapi.patch')
s=patch.read_text();assert '+++ b/'+relative not in s
s+=''.join(difflib.unified_diff(old.read_text().splitlines(True),new.read_text().splitlines(True),fromfile='a/'+relative,tofile='b/'+relative));patch.write_text(s)
for recipe in [HERE/'recipes/libcamera',SDK/'work/libcamera316-r25']:
 shutil.copyfile(patch,recipe/patch.name)
 p=recipe/'APKBUILD';text=p.read_text();lines=text.splitlines(True)
 for i,line in enumerate(lines):
  if line.endswith('  '+patch.name+'\n'):lines[i]=hashlib.sha512(patch.read_bytes()).hexdigest()+'  '+patch.name+'\n'
 p.write_text(''.join(lines))
target=SDK/'work/libcamera316-r25-built/src/libcamera-v0.7.2'/relative
assert target.read_bytes()==old.read_bytes();shutil.copyfile(new,target)
p=HERE/'package-source-validation.json';d=json.loads(p.read_text());d['changed_source_sha256'][relative]=hashlib.sha256(new.read_bytes()).hexdigest();p.write_text(json.dumps(d,indent=2)+'\n')
print('Added generic ISP ABI header with legacy type aliases; retained candidate updated.')
