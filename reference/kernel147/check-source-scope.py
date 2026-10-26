from pathlib import Path
import re, subprocess, json
k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
out=Path('/mnt/e/edk2-samurai-out/kernel147')
def split(data):
    return {b.split(b'\n',1)[0]:b for b in re.split(rb'(?m)(?=^diff --git )',data) if b}
prior=split((out / 'source145-restored-before-private.patch').read_bytes())
now=split(subprocess.check_output(['git','-C',str(k),'diff','--binary']))
names=['drivers/gpu/drm/msm/adreno/a6xx_gpu.c','drivers/gpu/drm/msm/msm_gem.h','drivers/gpu/drm/msm/msm_gem_vma.c']
keys={('diff --git a/'+n+' b/'+n).encode() for n in names}
assert set(prior)|keys==set(now)
assert all(now[x]==prior[x] for x in prior.keys()-keys)
assert (k / names[0]).read_text().count('a6xx_invalidate_ccu(')==0
report=dict(source_scope_pass=True,preexisting_other_diffs_preserved=True,ccu_order_restored=True,modified_files=names)
Path('/mnt/e/RealmeX2Pro edk2/reference/kernel147/source-scope-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('K147_SOURCE_SCOPE_VERIFIED')
