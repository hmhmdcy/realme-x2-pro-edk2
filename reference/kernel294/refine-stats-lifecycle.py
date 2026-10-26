from pathlib import Path
ROOT=Path(__file__).resolve().parent;D=Path('/home/cy122/x2pro-linux/camera279-isp-kernel/drivers/media/platform/qcom/camss')
def edit(name,old,new):
 p=D/name;s=p.read_text();assert s.count(old)==1,(name,old);p.write_text(s.replace(old,new))
# Validate under output_lock immediately before the output can become active.
p=D/'camss-vfe.h';s=p.read_text();needle='void (*vfe_output_start)';i=s.index(needle);i=s.rfind('\n',0,i)+1
s=s[:i]+'''\tint (*vfe_output_prepare)(struct vfe_device *vfe, struct vfe_output *output);
'''+s[i:];p.write_text(s)
edit('camss-vfe.c','''	unsigned int i;

	if (output->state > VFE_OUTPUT_RESERVED) {''','''	unsigned int i;
	int ret;

	if (ops->vfe_output_prepare) {
		ret = ops->vfe_output_prepare(vfe, output);
		if (ret)
			return ret;
	}
	if (output->state > VFE_OUTPUT_RESERVED) {''')
edit('camss-vfe-17x.c','\t.start_metadata = vfe_175_start_metadata,','\t.start_metadata = vfe_start_metadata_v2,')
needle='static void vfe_output_start_175('
p=D/'camss-vfe-17x.c';s=p.read_text();i=s.index(needle);s=s[:i]+'''static int vfe_output_prepare_175(struct vfe_device *vfe,
				  struct vfe_output *output)
{
	const struct vfe_175_stats_state *s = &vfe->pixel175.stats;
	int ret;

	if (output->pad == MSM_VFE_PAD_SRC_STATS) {
		ret = vfe_175_stats_validate_output(output);
		if (ret)
			return ret;
		return s->width >= 4 && s->height >= 2 ? 0 : -EINVAL;
	}
	if (output->line->is_pix)
		return vfe_175_validate_output(output);

	return 0;
}

'''+s[i:];p.write_text(s)
edit('camss-vfe-17x.c','\t.vfe_output_start = vfe_output_start_175,','\t.vfe_output_prepare = vfe_output_prepare_175,\n\t.vfe_output_start = vfe_output_start_175,')
p=D/'camss-vfe-175-stats.c';s=p.read_text();start=s.index('int vfe_175_start_metadata(');end=s.index('void vfe_175_stats_start(',start);s=s[:start]+s[end:]
old='''	/* Region offsets are pixels; sizes count 2x2 quads minus one. */
	writel_relaxed(s->left | ((u32)s->top << 16),
		       vfe->base + VFE_175_BHIST_OFFSET);
	writel_relaxed((s->width / 2 - 1) | ((s->height / 2 - 1) << 16),
		       vfe->base + VFE_175_BHIST_REGIONS);'''
new='''	/* Region offsets are pixels; sizes count 2x2 quads minus one. */
	value = readl_relaxed(vfe->base + VFE_175_BHIST_OFFSET);
	value &= ~(GENMASK(12, 0) | GENMASK(29, 16));
	value |= s->left | ((u32)s->top << 16);
	writel_relaxed(value, vfe->base + VFE_175_BHIST_OFFSET);
	value = readl_relaxed(vfe->base + VFE_175_BHIST_REGIONS);
	value &= ~(GENMASK(11, 0) | GENMASK(28, 16));
	value |= (s->width / 2 - 1) | ((s->height / 2 - 1) << 16);
	writel_relaxed(value, vfe->base + VFE_175_BHIST_REGIONS);'''
assert old in s;s=s.replace(old,new);p.write_text(s)
edit('camss-vfe-175-stats.h','int vfe_175_start_metadata(struct camss_video *vid);\n','')
for name in ['camss-vfe-175-stats.c','camss-vfe-175-stats.h']:(ROOT/name).write_bytes((D/name).read_bytes())
print('Output validation moved under output_lock; ROI reserved bits preserved.')
