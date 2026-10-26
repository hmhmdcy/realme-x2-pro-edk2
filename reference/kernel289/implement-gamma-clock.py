"""Clock Gamma SRAM during DMI uploads, then restore only the original clock policy."""
from pathlib import Path
import subprocess

TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel');ROOT=Path(__file__).resolve().parent
assert subprocess.check_output(['git','-C',str(TREE),'rev-parse','HEAD'],text=True).strip()=='8c79b7e1912790d3e18a84c9c6621a6d92baa768'
p=TREE/'drivers/media/platform/qcom/camss/camss-vfe-175-gamma.c';s=p.read_text()
s=s.replace('#define VFE_175_COLOR_ENABLE', '#define VFE_175_COLOR_CGC_OVERRIDE\t0x034\n#define VFE_175_COLOR_ENABLE',1)
s=s.replace('u32 lut_cfg, dmi_cfg, dmi_addr, value;', 'u32 lut_cfg, dmi_cfg, dmi_addr, cgc_override, value;')
needle='\t\tdmi_addr = readl_relaxed(vfe->base + VFE_175_DMI_ADDR);'
assert s.count(needle)==1
s=s.replace(needle,needle+'''
		/* SRAM access also needs the clock when no pixels are arriving yet. */
		cgc_override = readl_relaxed(vfe->base + VFE_175_COLOR_CGC_OVERRIDE);
		writel(cgc_override | VFE_175_COLOR_GAMMA,
		       vfe->base + VFE_175_COLOR_CGC_OVERRIDE);''')
needle='\t\twritel_relaxed(lut_cfg ^ VFE_175_RGB_LUT_BANKS,\n\t\t\t       vfe->base + VFE_175_RGB_LUT_CFG);'
assert s.count(needle)==1
s=s.replace(needle,needle+'''
		/* Complete the bank switch before returning to the saved clock policy. */
		writel(cgc_override, vfe->base + VFE_175_COLOR_CGC_OVERRIDE);''')
p.write_text(s)
patch=subprocess.check_output(['git','-C',str(TREE),'diff','--',str(p)])
(ROOT/'vfe175-gamma-clock-candidate.patch').write_bytes(patch)
print('Gamma clock candidate saved; curve and userspace unchanged, not deployed.')
