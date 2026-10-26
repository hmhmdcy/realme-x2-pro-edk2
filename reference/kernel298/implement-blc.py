"""Map common, equal WB subtraction to the VFE175 residual-black block."""
from pathlib import Path
import hashlib,json,subprocess
import host
HERE=Path(__file__).resolve().parent;TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
git=lambda *a:subprocess.check_output(['git','-C',str(TREE),*a],text=True).strip()
assert git('rev-parse','HEAD')=='ab709d9670f6dcaa71858fd4f3e189522f669913' and not git('status','--porcelain')
pins=json.loads((HERE.parent/'kernel297/blc-protocol-validation.json').read_text())
for row in pins['sources']:
 p=host.PRIVATE.parent/'kernel297'/(row['url'].rsplit('/',1)[-1]+'-reference-private');assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']
schema=host.PRIVATE.parent/'kernel297/bls_1_2_0.xsd-reference-private'
assert hashlib.sha256(schema.read_bytes()).hexdigest()=='5f9caa3c8c46fec4d87235e2dde334454a69c6fb09e962cd45c33e091dc81df1'
before=host.PRIVATE/'source-before298';assert not before.exists();before.mkdir()
d=TREE/'drivers/media/platform/qcom/camss'
for name in ['camss-vfe-175-pixel.c','camss-vfe-175-pixel.h']:(before/name).write_bytes((d/name).read_bytes())
subprocess.run(['git','-C',str(TREE),'switch','-c','samurai-blc298'],check=True)
p=d/'camss-vfe-175-pixel.h';s=p.read_text();needle='\tu16 r_gain;';assert needle in s
s=s.replace(needle,needle+'\n\tu16 black_level;');p.write_text(s)
p=d/'camss-vfe-175-pixel.c';s=p.read_text();needle='#define VFE_175_WB_GAIN_0'
defines='''#define VFE_175_LENS_ENABLE		0x040
#define VFE_175_BLC_ENABLE		BIT(11)
#define VFE_175_BLC_CONFIG		0x6b0
#define VFE_175_BLC_THRESHOLD_0	0x6b4
#define VFE_175_BLC_THRESHOLD_1	0x6b8
#define VFE_175_BLC_OFFSET		GENMASK(13, 0)
#define VFE_175_BLC_SCALE		GENMASK(31, 15)
#define VFE_175_BLC_THRESHOLDS	(GENMASK(13, 0) | GENMASK(29, 16))
#define VFE_175_BLC_UNITY		2048

'''
assert needle in s;s=s.replace(needle,defines+needle,1)
needle='static void vfe_175_wb_write('
helpers='''static u32 vfe_175_blc_level(u16 level)
{
	/* Common offsets are full-scale U16; the IFE processes U14 pixels. */
	return ((u32)level * 16383 + 32767) / 65535;
}

static void vfe_175_blc_enable(struct vfe_device *vfe, bool enable)
{
	u32 value = readl_relaxed(vfe->base + VFE_175_LENS_ENABLE);

	value &= ~VFE_175_BLC_ENABLE;
	if (enable)
		value |= VFE_175_BLC_ENABLE;
	writel_relaxed(value, vfe->base + VFE_175_LENS_ENABLE);
}

static void vfe_175_blc_write(struct vfe_device *vfe)
{
	const struct vfe_175_pixel_state *state = &vfe->pixel175;
	u32 level = state->wb_enabled ? vfe_175_blc_level(state->black_level) : 0;
	u32 value;

	value = readl_relaxed(vfe->base + VFE_175_BLC_CONFIG);
	value &= ~(VFE_175_BLC_OFFSET | VFE_175_BLC_SCALE);
	/* Preserve subtract-then-gain semantics; no implicit range stretch. */
	value |= FIELD_PREP(VFE_175_BLC_OFFSET, level) |
		 FIELD_PREP(VFE_175_BLC_SCALE, VFE_175_BLC_UNITY);
	writel_relaxed(value, vfe->base + VFE_175_BLC_CONFIG);
	/* Zero thresholds leave the optional per-channel clipping inactive. */
	value = readl_relaxed(vfe->base + VFE_175_BLC_THRESHOLD_0);
	writel_relaxed(value & ~VFE_175_BLC_THRESHOLDS,
		       vfe->base + VFE_175_BLC_THRESHOLD_0);
	value = readl_relaxed(vfe->base + VFE_175_BLC_THRESHOLD_1);
	writel_relaxed(value & ~VFE_175_BLC_THRESHOLDS,
		       vfe->base + VFE_175_BLC_THRESHOLD_1);
	vfe_175_blc_enable(vfe, level != 0);
}

'''
assert needle in s;s=s.replace(needle,helpers+needle,1)
needle='\tvalue = readl_relaxed(vfe->base + VFE_175_WB_GAIN_0);'
assert needle in s;s=s.replace(needle,'\tvfe_175_blc_write(vfe);\n\n'+needle,1)
s=s.replace('/* No offset conversion is advertised: only zero offsets are accepted. */','/* The separate BLS block performs the common pre-gain subtraction. */')
needle='\t    wb->g_sub || wb->b_sub || wb->r_sub ||'
assert needle in s;s=s.replace(needle,'\t    wb->g_sub != wb->b_sub || wb->g_sub != wb->r_sub ||',1)
needle='void vfe_175_pixel_stop(struct vfe_device *vfe)\n{'
assert needle in s;s=s.replace(needle,needle+'\n\tvfe_175_blc_enable(vfe, false);',1)
needle='\t\t\tvfe->pixel175.r_gain = wb->r_gain;'
assert needle in s;s=s.replace(needle,needle+'\n\t\t\tvfe->pixel175.black_level = wb->g_sub;',1)
p.write_text(s)
subprocess.run(['git','-C',str(TREE),'diff','--check'],check=True)
print(git('diff','--stat'))
