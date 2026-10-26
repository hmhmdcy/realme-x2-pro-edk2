"""Preserve the terminal r2 build, then prepare a narrow AF semantics correction."""
from pathlib import Path
import difflib,hashlib,json,shutil,subprocess
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
state=json.loads((P/'r24-r2-build-state-private.json').read_text());assert state['terminal'] and state['original214_files_links_modes_restored']
B=SDK/'work/libcamera278-r24-r2-built/src/libcamera-v0.7.2';O=SDK/'work/libcamera277-r23-built/src/libcamera-v0.7.2'
old=json.loads((R/'af-source-validation.json').read_text());assert all(hashlib.sha256((B/n).read_bytes()).hexdigest()==h for n,h in old['source_files'].items())
archive=P/'attempt2-sources';archive.mkdir(mode=0o700)
for n in ['af-source-validation.json','package-source-validation.json','r24-package-build-validation.json']:shutil.copyfile(R/n,archive/n)
shutil.copytree(R/'recipes',archive/'recipes')
q=subprocess.run(['python3',str(R/'prepare-af-patch.py')],capture_output=True);assert q.returncode==0,q.stderr.decode()
full=json.loads((R/'af-source-validation.json').read_text());temp=P/'r3-source';temp.mkdir(mode=0o700)
for name in full['source_before_files']:
 dest=temp/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(O/name,dest)
q=subprocess.run(['patch','--batch','--forward','-p1','-i',str(R/'0028-simple-contrast-autofocus.patch')],cwd=temp,capture_output=True,timeout=20)
(P/'r3-full-source-reproduction-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0
assert all(hashlib.sha256((temp/n).read_bytes()).hexdigest()==h for n,h in full['source_files'].items())
before={n:(B/n).read_text() for n in full['source_files']};after={n:(temp/n).read_text() for n in before};changed=[n for n in before if before[n]!=after[n]]
assert changed==['src/ipa/simple/soft_simple.cpp','src/ipa/libipa/contrast_af.h'],changed
patch=''.join(''.join(difflib.unified_diff(before[n].splitlines(True),after[n].splitlines(True),fromfile='a/'+n,tofile='b/'+n)) for n in changed)
(R/'af-r2-to-r3.patch').write_text(patch)
for recipe in [R/'recipes/libcamera',SDK/'work/libcamera278-r24']:
 p=recipe/'APKBUILD';lines=p.read_text().splitlines();indices=[i for i,l in enumerate(lines) if l.endswith('  0028-simple-contrast-autofocus.patch')];assert len(indices)==1
 lines[indices[0]]=hashlib.sha512((R/'0028-simple-contrast-autofocus.patch').read_bytes()).hexdigest()+'  0028-simple-contrast-autofocus.patch';p.write_text('\n'.join(lines)+'\n');shutil.copyfile(R/'0028-simple-contrast-autofocus.patch',recipe/'0028-simple-contrast-autofocus.patch')
proof=dict(full,source_before_files={n:hashlib.sha256(s.encode()).hexdigest() for n,s in before.items()},new_source_files=[],framework_version='99990.7.2-r24',config_version='0.1.0-r19',prior27_patches_retained=True,profile_only_in_device_data_package=True,phone_unchanged=True,build_attempt=3,incremental_source_cache='libcamera278-r24-r2-built',full_patch_reproduced_from_r23=True)
(R/'package-source-validation.json').write_text(json.dumps(proof,indent=2)+'\n')
for name in ['inspect-full-features.py','collect-forward-packages.py','host-runtime-qa.py']:
 p=R/name;s=p.read_text().replace('libcamera278-r24-r2-built','libcamera278-r24-r3-built').replace('packages278-r24-r2','packages278-r24-r3').replace('packages-config278-r24-r2','packages-config278-r24-r3');p.write_text(s)
(R/'r3-source-reproduction-validation.json').write_text(json.dumps(dict(stage=278,full_patch_reproduced_from_retained_r23=True,r2_build_terminal_and_sdk_restored=True,changed_files=changed,standard_cancel_ignored_outside_scan=True),indent=2)+'\n')
print('r3: full patch reproduced from r23; two-file delta from retained r2; cancel semantics corrected')
