"""Isolate the whole-frame DS4 precrop path without changing its filter or DMA."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
k=m.mounted_build().parent/'source354';git=lambda *a:subprocess.check_output(['git','-C',str(k),*a],text=True)
base='a993cd8a1db892bb5d68d9e6bcccfcc048aec9fd';assert git('rev-parse','HEAD').strip()==base and not git('status','--porcelain')
assert json.loads((P.parent/'kernel427/intree-build-state.json').read_text())['terminal']
for p in [k,*k.parents]:assert not (p/'AGENTS.md').exists()
subprocess.run(['git','-C',str(k),'switch','-c','samurai-ds4-precrop-isolation428'],check=True,capture_output=True)
rel='drivers/media/platform/qcom/camss/camss-vfe-175-ds4.c';p=k/rel;t=p.read_text()
old='\twritel_relaxed((value & ~0xa0U) | 0x5500, vfe->base + 0x4c);';assert t.count(old)==1
new='''	value &= ~0xa0U;
	/* The current FULL backend rejects ROI. For complete 8-pixel groups,
	 * this window covers the whole scaler output and can be bypassed.
	 * Keep the existing crop path for partial groups until verified. */
	if (!((full->width | full->height) & 7))
		value = (value & ~BIT(8)) | 0x5400;
	else
		value |= 0x5500;
	writel_relaxed(value, vfe->base + 0x4c);'''
p.write_text(t.replace(old,new));subprocess.run(['git','-C',str(k),'add','--',rel],check=True)
subprocess.run(['git','-C',str(k),'commit','-m','media: camss: isolate redundant full-frame DS4 precrop'],check=True)
state=dict(stage=428,parent_commit=base,commit=git('rev-parse','HEAD').strip(),branch=git('branch','--show-current').strip(),source_hashes=[dict(path=rel,sha256=hashlib.sha256(p.read_bytes()).hexdigest())],
 whole_frame_aligned_precrop_bypass_diagnostic=True,partial_groups_keep_prior_path=True,filter_depth_packer_dma_and_uapi_unchanged=True,
 original_crop_geometry_production_not_claimed=True,hardware_validated=False,installed=False,passed=True)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n');(HERE/'precrop-isolation.patch').write_text(git('diff',base,'HEAD'))
text=(HERE.parent/'kernel427/build-intree.py').read_text().replace('stage=427','stage=428');(HERE/'build-intree.py').write_text(text)
text=(HERE.parent/'kernel427/check-runtime.py').read_text().replace('stage=427','stage=428')
text=text.replace("+(HERE/'runtime-contract.c').read_text()","+(HERE/'runtime-contract.c').read_text()")
(HERE/'check-runtime.py').write_text(text.replace('native_precrop_ds4_depth_and_r2pd_match=True','native_precrop_data_filter_depth_and_r2pd_match=True,whole_frame_aligned_precrop_switch_bypassed=True,partial_group_precrop_switch_unchanged=True'))
text=(HERE.parent/'kernel427/runtime-contract.c').read_text().replace('mmio[0x4c/4]==0x80005518','mmio[0x4c/4]==(((in[0]|in[1])&7)?0x80005518:0x80005418)');(HERE/'runtime-contract.c').write_text(text)
text=(HERE.parent/'kernel427/prepare-capture.py').read_text().replace("'stage':427","'stage':428").replace('k427-ds4-','k428-ds4-');(HERE/'prepare-capture.py').write_text(text)
print(json.dumps(state,indent=2))
