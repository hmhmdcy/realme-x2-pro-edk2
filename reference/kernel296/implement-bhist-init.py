"""Initialize VFE175 histogram SRAM before pixels arrive, using pinned protocol facts."""
from pathlib import Path
import json,subprocess
ROOT=Path(__file__).resolve().parent;TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
git=lambda *a:subprocess.check_output(['git','-C',str(TREE),*a],text=True).strip()
assert git('rev-parse','HEAD')=='d249946aefa1a01d99fd5484825a4458423b7348' and not git('status','--porcelain')
facts=json.loads((ROOT/'dmi-protocol-sources.json').read_text())['numeric_protocol_definitions']
assert [facts[n] for n in ['regIFE_IFE_0_VFE_DMI_CFG','regIFE_IFE_0_VFE_DMI_ADDR','regIFE_IFE_0_VFE_DMI_DATA_LO','IFE_IFE_0_VFE_DMI_CFG_DMI_RAM_SEL_STATS_BHIST_RAM']]==[0xc24,0xc28,0xc30,0x3a]
assert facts['IFE_IFE_0_VFE_MODULE_STATS_CGC_OVERRIDE_SKIN_BHIST_CGC_OVERRIDE_MASK']==16
subprocess.run(['git','-C',str(TREE),'switch','-c','samurai-stats296'],check=True)
p=TREE/'drivers/media/platform/qcom/camss/camss-vfe-175-stats.c';s=p.read_text()
needle='#define VFE_175_STATS_CONFIG             0xaac'
assert needle in s
s=s.replace(needle,'''#define VFE_175_STATS_CGC                0x030
#define VFE_175_DMI_CONFIG               0xc24
#define VFE_175_DMI_ADDRESS              0xc28
#define VFE_175_DMI_DATA_LOW             0xc30
#define VFE_175_DMI_RAM_SELECT           GENMASK(6, 0)
#define VFE_175_DMI_AUTO_INCREMENT       BIT(8)
#define VFE_175_DMI_AUTO_LOAD            BIT(12)
#define VFE_175_DMI_BHIST_RAM            0x3a
'''+needle,1)
helper='''/* The register reset does not initialize the histogram counter SRAM. */
static void vfe_175_bhist_clear(struct vfe_device *vfe)
{
	u32 cgc = readl_relaxed(vfe->base + VFE_175_STATS_CGC);
	u32 config = readl_relaxed(vfe->base + VFE_175_DMI_CONFIG);
	u32 address = readl_relaxed(vfe->base + VFE_175_DMI_ADDRESS);
	u32 select;
	unsigned int i;

	/* Pre-stream setup owns DMI; keep the SRAM clock on during CPU access. */
	writel(cgc | VFE_175_BHIST_ENABLE, vfe->base + VFE_175_STATS_CGC);
	select = config & ~(VFE_175_DMI_RAM_SELECT |
			    VFE_175_DMI_AUTO_INCREMENT | VFE_175_DMI_AUTO_LOAD);
	writel(select | VFE_175_DMI_BHIST_RAM, vfe->base + VFE_175_DMI_CONFIG);
	for (i = 0; i < CAMSS_STATS_BHIST_BINS; i++) {
		/* Explicit indices avoid inheriting another DMI user's mode. */
		writel(i, vfe->base + VFE_175_DMI_ADDRESS);
		writel(0, vfe->base + VFE_175_DMI_DATA_LOW);
	}
	/* Complete SRAM writes before restoring shared state and clock policy. */
	readl(vfe->base + VFE_175_DMI_CONFIG);
	writel(config, vfe->base + VFE_175_DMI_CONFIG);
	writel(address, vfe->base + VFE_175_DMI_ADDRESS);
	writel(cgc, vfe->base + VFE_175_STATS_CGC);
}

'''
needle='static void vfe_175_bhist_write(';assert needle in s;s=s.replace(needle,helper+needle,1)
needle='''	if (valid)
		vfe_175_bhist_write(vfe, line);'''
assert needle in s;s=s.replace(needle,'''	if (valid) {
		vfe_175_bhist_clear(vfe);
		vfe_175_bhist_write(vfe, line);
	}''',1)
p.write_text(s)
(ROOT/'bhist-init-candidate.patch').write_bytes(subprocess.check_output(['git','-C',str(TREE),'diff']))
print('Added pre-stream SRAM initialization in the SoC driver; not committed or deployed yet.')
