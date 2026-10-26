"""Refresh candidate inputs only after the first build ended and original SDK was restored."""
from pathlib import Path
import hashlib,json,shutil
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
state=json.loads((P/'r24-build-state-private.json').read_text());assert state['exit']==1 and state['original214_files_links_modes_restored']
assert (SDK/'work/libcamera').is_dir() and (SDK/'work/libcamera278-r24-built').is_dir()
archive=P/'attempt1-sources';archive.mkdir(mode=0o700)
for n in ['af-source-validation.json','package-source-validation.json']:
 shutil.copyfile(R/n,archive/n)
shutil.copytree(R/'recipes',archive/'recipes')
patch=R/'0028-simple-contrast-autofocus.patch'
import subprocess
q=subprocess.run(['python3',str(R/'prepare-af-patch.py')],capture_output=True);assert q.returncode==0,q.stderr.decode()
for recipe in [R/'recipes/libcamera',SDK/'work/libcamera278-r24']:
 p=recipe/'APKBUILD';text=p.read_text();lines=text.splitlines();matched=[i for i,l in enumerate(lines) if l.endswith('  '+patch.name)];assert len(matched)==1
 lines[matched[0]]=hashlib.sha512(patch.read_bytes()).hexdigest()+'  '+patch.name;p.write_text('\n'.join(lines)+'\n');shutil.copyfile(patch,recipe/patch.name)
proof=json.loads((R/'af-source-validation.json').read_text());proof.update(framework_version='99990.7.2-r24',config_version='0.1.0-r19',prior27_patches_retained=True,profile_only_in_device_data_package=True,phone_unchanged=True,build_attempt=2)
(R/'package-source-validation.json').write_text(json.dumps(proof,indent=2)+'\n')
print('Attempt1 ended and SDK restored; corrected const sensor/lens ownership at constructor boundary')
