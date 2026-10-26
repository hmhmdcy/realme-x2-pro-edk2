from pathlib import Path
import difflib,json,subprocess
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel147'); out=Path('/mnt/e/edk2-samurai-out/kernel147')
k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
validation=json.loads((ref / 'gpu-regression-validation.json').read_text())
assert validation['device_fix_accepted'] and validation['total_process_exits']==26
names=json.loads((ref / 'source-scope-validation.json').read_text())['modified_files']
source=k / names[0]
old='/* Diagnostic candidate: test A640 GMEM resolve address granularity. */'
new='/* A640 GMEM resolves fault on unaligned legacy BO starts. */'
s=source.read_text(); assert s.count(old)==1
source.write_text(s.replace(old,new))
patch=''
for name in names:
    before=(out / (Path(name).name+'-before-private')).read_text()
    after=(k / name).read_text()
    patch+='diff --git a/'+name+' b/'+name+'\n'+''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+name,tofile='b/'+name))
subprocess.run(['git','-C',str(k),'diff','--check','--',*names],check=True)
(ref / 'a640-managed-iova-alignment.patch').write_text(patch)
preparation=json.loads((ref / 'candidate-preparation.json').read_text())
preparation.update(candidate_diagnostic_only=False,device_fix_accepted=True)
(ref / 'candidate-preparation.json').write_text(json.dumps(preparation,indent=2)+'\n')
build=json.loads((ref / 'build-package-validation.json').read_text())
build.update(diagnostic_candidate=False,device_fix_accepted=True,source_comment_only_updated_after_validation=True,compiled_behavior_unchanged=True)
for p in [ref,out]: (p / 'build-package-validation.json').write_text(json.dumps(build,indent=2)+'\n')
print('K147_VALIDATED_GPU_FIX_PATCH_READY')
