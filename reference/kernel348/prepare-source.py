"""Add segmented IFE Gamma through the existing typed parameter queue."""
from pathlib import Path
import importlib.util,json,shutil,subprocess
import host
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
build=storage.mounted_build();parent=build.parent/'source338';tree=build.parent/'source348'
base='e3aa81b109e44735161036a2adede105e437ed01'
assert subprocess.check_output(['git','-C',str(parent),'rev-parse','HEAD'],text=True).strip()==base
assert not subprocess.check_output(['git','-C',str(parent),'diff','HEAD'])
directory=Path('drivers/media/platform/qcom/camss');uapi=Path('include/uapi/linux/qcom-camss-config.h')
for relative in [Path('.'),*directory.parents,directory,*uapi.parent.parents,uapi.parent]:
 p=parent/relative/'AGENTS.md'
 if p.exists():raise RuntimeError('Read applicable instructions before preparing source: '+str(p))
if tree.exists():
 assert subprocess.check_output(['git','-C',str(tree),'rev-parse','HEAD'],text=True).strip()==base
 assert not subprocess.check_output(['git','-C',str(tree),'diff','HEAD'])
else:subprocess.run(['git','-C',str(parent),'worktree','add','-b','samurai-ife-gamma348',str(tree),base],check=True)
changed=[]
def edit(relative,before,after):
 p=tree/relative;s=p.read_text();assert s.count(before)==1,(str(relative),before)
 p.write_text(s.replace(before,after))
 if relative not in changed:changed.append(relative)
edit(uapi,' * @CAMSS_PARAMS_LSC: regular lens shading mesh, &struct camss_params_lsc',
 ' * @CAMSS_PARAMS_LSC: regular lens shading mesh, &struct camss_params_lsc\n * @CAMSS_PARAMS_IFE_GAMMA: segmented IFE RGB gamma,\n *\t&struct camss_params_ife_gamma')
edit(uapi,'\tCAMSS_PARAMS_LSC = 6,','\tCAMSS_PARAMS_LSC = 6,\n\tCAMSS_PARAMS_IFE_GAMMA = 7,')
needle='#define CAMSS_PARAMS_IFE_COLOR_MAX_PAYLOAD \\\n\t(CAMSS_PARAMS_IFE_LSC_MAX_PAYLOAD + sizeof(struct camss_params_color_correct))'
new='''
/* IFE Gamma uses uniformly spaced segments, unlike the OPE direct LUT. */
#define CAMSS_IFE_GAMMA_CHANNELS 3
#define CAMSS_IFE_GAMMA_SEGMENTS 64

/**
 * struct camss_ife_gamma_segment - one linear segment in a 10-bit output domain
 * @base: output at the segment's lower endpoint, 0 through 1023
 * @delta: signed output change over the segment, -512 through 511
 *
 * Each segment covers 1/64 of the full input range. The last delta describes
 * the change toward the full-scale endpoint, which may reach 1024. Segments
 * are independent: no continuity or monotonicity is imposed by this ABI.
 */
struct camss_ife_gamma_segment {
\t__u16 base;
\t__s16 delta;
};

/**
 * struct camss_params_ife_gamma - segmented RGB gamma curves for IFE
 * @header: block header; type is CAMSS_PARAMS_IFE_GAMMA
 * @segments: 64 segments per channel, in R, G, B channel order
 *
 * ENABLE uploads and enables. With neither flag, upload retains the current
 * enable state. DISABLE accepts a header-only block and leaves stored curves
 * intact. Reopening a stream restores its format's initial transfer curve.
 */
struct camss_params_ife_gamma {
\tstruct v4l2_isp_params_block_header header;
\tstruct camss_ife_gamma_segment
\t\tsegments[CAMSS_IFE_GAMMA_CHANNELS][CAMSS_IFE_GAMMA_SEGMENTS];
} __attribute__((aligned(8)));

#define CAMSS_PARAMS_IFE_GAMMA_MAX_PAYLOAD \\
\t(CAMSS_PARAMS_IFE_COLOR_MAX_PAYLOAD + sizeof(struct camss_params_ife_gamma))
'''
edit(uapi,needle,needle+'\n'+new)
edit(directory/'camss-vfe-175-pixel.h','\tbool wb_enabled;','\tbool wb_enabled;\n\tbool gamma_enabled;')
edit(directory/'camss-vfe-175-pixel.h','vfe_175_params_info[7]','vfe_175_params_info[8]')
edit(directory/'camss-vfe-175-pixel.c','vfe_175_params_info[7]','vfe_175_params_info[8]')
needle='\t[CAMSS_PARAMS_LSC] = {'
edit(directory/'camss-vfe-175-pixel.c',needle,'''\t[CAMSS_PARAMS_IFE_GAMMA] = {
\t\t.size = sizeof(struct camss_params_ife_gamma),
\t\t.block_validate = vfe_175_gamma_validate,
\t},
'''+needle)
edit(directory/'camss-vfe-175-pixel.c','\t\t.wb_enabled = true,','\t\t.wb_enabled = true,\n\t\t.gamma_enabled = true,')
needle='\t\tif (block->type == CAMSS_PARAMS_COLOR_CORRECT) {'
edit(directory/'camss-vfe-175-pixel.c',needle,'''\t\tif (block->type == CAMSS_PARAMS_IFE_GAMMA) {
\t\t\tvfe_175_gamma_params(vfe, block);
\t\t\toffset += block->size;
\t\t\tcontinue;
\t\t}
'''+needle)
edit(directory/'camss-vfe-17x.c','\t.params_max_payload = CAMSS_PARAMS_IFE_COLOR_MAX_PAYLOAD,','\t.params_max_payload = CAMSS_PARAMS_IFE_GAMMA_MAX_PAYLOAD,')
edit(directory/'camss-vfe-175-gamma.h','struct vfe_device;','struct device;\nstruct v4l2_isp_block_header;\nstruct vfe_device;')
edit(directory/'camss-vfe-175-gamma.h','void vfe_175_gamma_stop(struct vfe_device *vfe);',
 '''int vfe_175_gamma_validate(struct device *dev,
\t\t\t   const struct v4l2_isp_block_header *block);
void vfe_175_gamma_params(struct vfe_device *vfe,
\t\t\t  const struct v4l2_isp_block_header *block);
void vfe_175_gamma_stop(struct vfe_device *vfe);''')
edit(directory/'camss-vfe-175-gamma.c','#include <linux/io.h>','#include <linux/io.h>\n#include <linux/qcom-camss-config.h>')
p=tree/directory/'camss-vfe-175-gamma.c';s=p.read_text()
start=s.index('int vfe_175_gamma_configure(');end=s.index('void vfe_175_gamma_stop(',start)
old=s[start:end]
upload_start=old.index('\t\tlut_cfg =');upload_end=old.index('\n\t}\n\t/* Publish',upload_start)
body=old[upload_start:upload_end]
body='\n'.join(line[1:] if line.startswith('\t') else line for line in body.splitlines())
body=body.replace('/* Caller owns pre-stream setup; no concurrent DMI consumer yet. */',
 '/* Pre-stream setup or output_lock owns this shared DMI transaction. */')
replacement='''static void vfe_175_gamma_enable(struct vfe_device *vfe, bool enable)
{
\tu32 value = readl_relaxed(vfe->base + VFE_175_COLOR_ENABLE);

\tvalue &= ~VFE_175_COLOR_GAMMA;
\tif (enable)
\t\tvalue |= VFE_175_COLOR_GAMMA;
\twritel_relaxed(value, vfe->base + VFE_175_COLOR_ENABLE);
}

static void vfe_175_gamma_upload(struct vfe_device *vfe,
\t\t\t\t const u32 packed[3][VFE_175_GAMMA_ENTRIES])
{
\t/* LUT_CFG banks are R/G/B; DMI memory selectors are R30/G26/B28. */
\tstatic const u8 selectors[3] = { 30, 26, 28 };
\tu32 lut_cfg, dmi_cfg, dmi_addr, cgc_override;
\tunsigned int ch, i;

'''+body+'''
}

int vfe_175_gamma_configure(struct vfe_device *vfe,
\t\t\t   const struct vfe_175_gamma_config *config)
{
\tu32 packed[3][VFE_175_GAMMA_ENTRIES];
\tint ret;

\tif (!vfe_175_gamma_supported(vfe))
\t\treturn -EINVAL;
\tret = vfe_175_gamma_pack(config, packed);
\tif (ret)
\t\treturn ret;
\tif (config->enabled)
\t\tvfe_175_gamma_upload(vfe, packed);
\t/* Publish the bank/configuration before enabling Gamma; no PIX RUP. */
\twmb();
\tvfe->pixel175.gamma_enabled = config->enabled;
\tvfe_175_gamma_enable(vfe, config->enabled);
\treturn 0;
}

int vfe_175_gamma_validate(struct device *dev,
\t\t\t   const struct v4l2_isp_block_header *block)
{
\tconst struct camss_params_ife_gamma *gamma;
\tunsigned int ch, i;

\tif (block->flags & ~(V4L2_ISP_PARAMS_FL_BLOCK_ENABLE |
\t\t\t     V4L2_ISP_PARAMS_FL_BLOCK_DISABLE) ||
\t    block->flags == (V4L2_ISP_PARAMS_FL_BLOCK_ENABLE |
\t\t\t     V4L2_ISP_PARAMS_FL_BLOCK_DISABLE))
\t\treturn -EINVAL;
\tif (block->flags & V4L2_ISP_PARAMS_FL_BLOCK_DISABLE)
\t\treturn 0;
\tgamma = container_of(block, struct camss_params_ife_gamma, header);
\tfor (ch = 0; ch < CAMSS_IFE_GAMMA_CHANNELS; ch++)
\t\tfor (i = 0; i < CAMSS_IFE_GAMMA_SEGMENTS; i++) {
\t\t\tconst struct camss_ife_gamma_segment *segment =
\t\t\t\t&gamma->segments[ch][i];

\t\t\tif (segment->base > 1023 || segment->delta < -512 ||
\t\t\t    segment->delta > 511)
\t\t\t\treturn -EINVAL;
\t\t}
\treturn 0;
}

void vfe_175_gamma_params(struct vfe_device *vfe,
\t\t\t  const struct v4l2_isp_block_header *block)
{
\tconst struct camss_params_ife_gamma *gamma;
\tu32 packed[3][VFE_175_GAMMA_ENTRIES];
\tunsigned int ch, i;

\tif (block->flags & V4L2_ISP_PARAMS_FL_BLOCK_DISABLE) {
\t\tvfe->pixel175.gamma_enabled = false;
\t\tvfe_175_gamma_enable(vfe, false);
\t\treturn;
\t}
\tgamma = container_of(block, struct camss_params_ife_gamma, header);
\tfor (ch = 0; ch < CAMSS_IFE_GAMMA_CHANNELS; ch++)
\t\tfor (i = 0; i < CAMSS_IFE_GAMMA_SEGMENTS; i++) {
\t\t\tconst struct camss_ife_gamma_segment *segment =
\t\t\t\t&gamma->segments[ch][i];

\t\t\tpacked[ch][i] = segment->base |
\t\t\t\t((u32)segment->delta & 0x3ff) << 10;
\t\t}
\t/* The normal parameter queue serializes this with LSC and issues PIX RUP. */
\tvfe_175_gamma_upload(vfe, packed);
\tif (block->flags & V4L2_ISP_PARAMS_FL_BLOCK_ENABLE)
\t\tvfe->pixel175.gamma_enabled = true;
\t/* Publish the completed LUT bank before its enable state. */
\twmb();
\tvfe_175_gamma_enable(vfe, vfe->pixel175.gamma_enabled);
}

'''
s=s[:start]+replacement+s[end:]
start=s.index('void vfe_175_gamma_stop(')
s=s[:start]+'''void vfe_175_gamma_stop(struct vfe_device *vfe)
{
\tif (!vfe_175_gamma_supported(vfe))
\t\treturn;
\tvfe->pixel175.gamma_enabled = false;
\tvfe_175_gamma_enable(vfe, false);
}
'''
p.write_text(s)
edit(directory/'camss-vfe-175-lsc.c','/* output_lock serializes parameters; Gamma only uses DMI before PIX starts. */',
 '/* output_lock serializes this shared DMI transaction with Gamma. */')
for relative in changed:
 target=HERE/'kernel'/relative.name;target.parent.mkdir(exist_ok=True);shutil.copyfile(tree/relative,target)
(HERE/'ife-gamma-driver.patch').write_bytes(subprocess.check_output(['git','-C',str(tree),'diff','HEAD']))
(HERE/'source-state.json').write_text(json.dumps(dict(stage=348,source=str(tree),base_commit=base,branch='samurai-ife-gamma348',
 changed_sources=[str(r) for r in changed],new_parameter_type=7,new_block_bytes=776,
 native_rgb_channels=3,native_segments=64,installed=False,board_and_sensor_changes=False),indent=2)+'\n')
print('Prepared segmented IFE Gamma UAPI/backend; shared DMI uses the existing parameter lock and RUP lifecycle.')
