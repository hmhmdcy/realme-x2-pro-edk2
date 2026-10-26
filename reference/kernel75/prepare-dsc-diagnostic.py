from pathlib import Path
import difflib, hashlib, json, urllib.request

root=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel75')
out=Path('/mnt/e/edk2-samurai-out/kernel75')
kernel=Path('/home/cy122/x2pro-linux/linux')
relative='drivers/gpu/drm/msm/disp/dpu1/dpu_hw_dsc.c'
p=kernel/relative
before=p.read_text()
backup=out/'dpu_hw_dsc.c.before'
assert not backup.exists(), 'Do not overwrite the original backup'
assert before.count('c->caps = cfg;')==1
after=before.replace('c->caps = cfg;', '''c->caps = cfg;

	if (mdss_ver->core_major_ver == 5)
		pr_info("boot DSC%u: mode=%#x enc=%#x pic=%#x slice=%#x chunk=%#x delay=%#x flat=%#x mux=%#x\\n",
			cfg->id - DSC_0,
			DPU_REG_READ(&c->hw, DSC_COMMON_MODE),
			DPU_REG_READ(&c->hw, DSC_ENC),
			DPU_REG_READ(&c->hw, DSC_PICTURE),
			DPU_REG_READ(&c->hw, DSC_SLICE),
			DPU_REG_READ(&c->hw, DSC_CHUNK_SIZE),
			DPU_REG_READ(&c->hw, DSC_DELAY),
			DPU_REG_READ(&c->hw, DSC_FLATNESS),
			DPU_REG_READ(&c->hw, DSC_CTL(c->idx)));''')
backup.write_text(before)
p.write_text(after)
patch='diff --git a/'+relative+' b/'+relative+'\n'+''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),'a/'+relative,'b/'+relative))
(root/'dsc-diagnostic.patch').write_text(patch)
build=(root/'build-matched.sh').read_text().replace('matched','dsc-diag')
(root/'build-dsc-diag.sh').write_text(build)
print('Added read-only SM8150 boot DSC register diagnostics')

url='https://raw.githubusercontent.com/realme-kernel-opensource/realmeX2Pro-kernel-source/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/drivers/gpu/drm/msm/dsi-staging/dsi_panel.c'
sp=out/'stock-dsi_panel.c'
if not sp.exists():
    sp.write_bytes(urllib.request.urlopen(url,timeout=30).read())
lines=sp.read_text().splitlines()
for i,line in enumerate(lines):
    if any(x in line for x in ('slice_last_group_size =','det_thresh_flatness =','input_10_bits =')):
        print('\n'.join(f'{j+1}: {lines[j]}' for j in range(max(0,i-4),min(len(lines),i+6))))
