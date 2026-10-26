"""Expose the implemented single FULL NV12 path through standard CAMSS resources."""
from pathlib import Path
import subprocess

TREE = Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
BASE = '6ddf1ba4cfafe221a38cc12667a1aac06f3f9ec5'
git = lambda *a: subprocess.check_output(['git', '-C', str(TREE), *a], text=True).strip()
assert git('rev-parse', 'HEAD') == BASE and not git('status', '--porcelain')
subprocess.run(['git', '-C', str(TREE), 'switch', '-c', 'samurai-vfe175-pix288'], check=True)
D = TREE/'drivers/media/platform/qcom/camss'

def replace(name, before, after, count=1):
    p = D/name
    s = p.read_text()
    assert s.count(before) == count, (name, before[:90], s.count(before))
    p.write_text(s.replace(before, after))

replace('camss-vfe.h', '\tconst struct camss_formats *formats_pix;\n',
'''\tconst struct camss_formats *formats_pix;
\t/* Optional processed output formats, separate from PIX sink formats. */
\tconst struct camss_formats *formats_pix_out;
\tconst struct v4l2_frmsize_stepwise *pix_frame_sizes;
\tbool pix_no_crop;
''')
replace('camss-vfe.h', 'extern const struct camss_formats vfe_formats_pix_845;',
'''extern const struct camss_formats vfe_formats_pix_845;
extern const struct camss_formats vfe_formats_pix_175;
extern const struct camss_formats vfe_formats_pix_out_175;
extern const struct v4l2_frmsize_stepwise vfe_frame_sizes_pix_175;''')
replace('camss-video.h', '\tunsigned int line_based;\n',
'''\tunsigned int line_based;
\t/* Optional per-output bounds and dimension steps; NULL keeps legacy limits. */
\tconst struct v4l2_frmsize_stepwise *frame_sizes;
''')
replace('camss-vfe.c', '''\tstruct vfe_device *vfe = to_vfe(line);

\tswitch (vfe->camss->res->version) {''',
'''\tstruct vfe_device *vfe = to_vfe(line);
\tconst struct camss_formats *out = vfe->res->formats_pix_out;
\tunsigned int i;

\tif (line->is_pix && out) {
\t\tfor (i = 0; i < out->nformats; i++)
\t\t\tif (out->formats[i].code == src_req_code)
\t\t\t\treturn src_req_code;
\t\treturn index < out->nformats ? out->formats[index].code : 0;
\t}

\tswitch (vfe->camss->res->version) {''')
replace('camss-vfe.c', '''\t\t/* If not found, use UYVY as default */
\t\tif (i >= line->nformats)
\t\t\tfmt->code = MEDIA_BUS_FMT_UYVY8_1X16;''',
'''\t\t/* A processed-only PIX input must fall back to a supported Bayer code. */
\t\tif (i >= line->nformats) {
\t\t\tif (line->is_pix && to_vfe(line)->res->formats_pix_out)
\t\t\t\tfmt->code = line->formats[0].code;
\t\t\telse
\t\t\t\tfmt->code = MEDIA_BUS_FMT_UYVY8_1X16;
\t\t}''')
replace('camss-vfe.c', '''\tif (rect->height < 4)
\t\trect->height = 4;
}

/*
 * vfe_try_crop''',
'''\tif (rect->height < 4)
\t\trect->height = 4;

\tif (to_vfe(line)->res->pix_frame_sizes) {
\t\tconst struct v4l2_frmsize_stepwise *s = to_vfe(line)->res->pix_frame_sizes;

\t\trect->width = clamp_t(u32, rect->width, s->min_width, s->max_width);
\t\trect->height = clamp_t(u32, rect->height, s->min_height, s->max_height);
\t\trect->width -= (rect->width - s->min_width) % s->step_width;
\t\trect->height -= (rect->height - s->min_height) % s->step_height;
\t}
}

/*
 * vfe_try_crop''')
replace('camss-vfe.c', '''\tcompose = __vfe_get_compose(line, sd_state, which);

\tif (rect->width > compose->width)''',
'''\tcompose = __vfe_get_compose(line, sd_state, which);

\tif (to_vfe(line)->res->pix_no_crop) {
\t\t*rect = *compose;
\t\treturn;
\t}

\tif (rect->width > compose->width)''')
replace('camss-vfe.c', '''\t\tvideo_out->nformats = vfe->line[i].nformats;
\t\tvideo_out->formats = vfe->line[i].formats;''',
'''\t\tvideo_out->nformats = vfe->line[i].nformats;
\t\tvideo_out->formats = vfe->line[i].formats;
\t\tif (vfe->line[i].is_pix && vfe->res->formats_pix_out) {
\t\t\tvideo_out->nformats = vfe->res->formats_pix_out->nformats;
\t\t\tvideo_out->formats = vfe->res->formats_pix_out->formats;
\t\t\tvideo_out->frame_sizes = vfe->res->pix_frame_sizes;
\t\t}''')
replace('camss-video.c', '''\tfsize->stepwise.step_height = 1;

\treturn 0;''',
'''\tfsize->stepwise.step_height = 1;
\tif (video->frame_sizes) {
\t\tfsize->type = V4L2_FRMSIZE_TYPE_STEPWISE;
\t\tfsize->stepwise = *video->frame_sizes;
\t}

\treturn 0;''')
replace('camss-video.c', '''\tpix_mp->height = clamp_t(u32, height, 1, CAMSS_FRAME_MAX_HEIGHT_RDI);
\tpix_mp->num_planes = fi->planes;''',
'''\tpix_mp->height = clamp_t(u32, height, 1, CAMSS_FRAME_MAX_HEIGHT_RDI);
\tif (video->frame_sizes) {
\t\tconst struct v4l2_frmsize_stepwise *s = video->frame_sizes;

\t\tpix_mp->width = clamp_t(u32, width, s->min_width, s->max_width);
\t\tpix_mp->height = clamp_t(u32, height, s->min_height, s->max_height);
\t\tpix_mp->width -= (pix_mp->width - s->min_width) % s->step_width;
\t\tpix_mp->height -= (pix_mp->height - s->min_height) % s->step_height;
\t}
\tpix_mp->num_planes = fi->planes;''')
replace('camss-vfe-17x.c', '''\tvfe->isr_ops.comp_done = vfe_175_comp_done;
}''',
'''\tvfe->isr_ops.comp_done = vfe_175_comp_done;
\tif (!vfe->res->is_lite && vfe->res->line_num > VFE_LINE_PIX) {
\t\tstruct vfe_line *pix = &vfe->line[VFE_LINE_PIX];

\t\tvfe_add_yuv(&pix->output[0], 3, 4, 0);
\t\tvfe_set_pix(pix, 1);
\t\t/* Only sink and FULL are implemented; no DS or metadata pads yet. */
\t\tpix->num_pads = MSM_VFE_PAD_NUM_RDI;
\t}
}''')
# Only the two SM8150 full-IFE resources change; RDI numbering remains 0..2.
p = D/'camss.c'
s = p.read_text()
start = s.index('static const struct camss_subdev_resources vfe_res_8150[]')
end = s.index('static const struct camss_subdev_resources', start+20)
section = s[start:end]
assert section.count('.line_num = 3,') == 2
assert section.count('.formats_pix = &vfe_formats_rdi_845') == 2
section = section.replace('.line_num = 3,', '.line_num = 4,')
section = section.replace('.formats_pix = &vfe_formats_rdi_845',
''' .formats_pix = &vfe_formats_pix_175,
\t\t\t.formats_pix_out = &vfe_formats_pix_out_175,
\t\t\t.pix_frame_sizes = &vfe_frame_sizes_pix_175,
\t\t\t.pix_no_crop = true'''.lstrip())
p.write_text(s[:start]+section+s[end:])

p = D/'camss-vfe-175-output.c'
s = p.read_text()
at = s.index('int vfe_175_validate_output')
raw = []
for depth in [8, 10, 12, 14]:
    for cfa in ['SBGGR', 'SGBRG', 'SGRBG', 'SRGGB']:
        suffix = '' if depth == 8 else 'P'
        raw.append(f'\t{{ MEDIA_BUS_FMT_{cfa}{depth}_1X{depth}, {depth}, V4L2_PIX_FMT_{cfa}{depth}{suffix}, 1,\n\t  PER_PLANE_DATA(0, 1, 1, 1, 1, {depth}) }},')
tables = '''/* Input and output format sets describe different sides of the ISP. */
static const struct camss_format_info formats_pix_175[] = {
'''+ '\n'.join(raw)+'''
};

static const struct camss_format_info formats_pix_out_175[] = {
\t{ MEDIA_BUS_FMT_UYVY8_1_5X8, 8, V4L2_PIX_FMT_NV12, 1,
\t  PER_PLANE_DATA(0, 1, 1, 2, 3, 8) },
};

const struct camss_formats vfe_formats_pix_175 = {
\t.nformats = ARRAY_SIZE(formats_pix_175),
\t.formats = formats_pix_175,
};

const struct camss_formats vfe_formats_pix_out_175 = {
\t.nformats = ARRAY_SIZE(formats_pix_out_175),
\t.formats = formats_pix_out_175,
};

const struct v4l2_frmsize_stepwise vfe_frame_sizes_pix_175 = {
\t.min_width = 16,
\t.max_width = VFE_175_FULL_MAX_WIDTH,
\t.step_width = 16,
\t.min_height = 4,
\t.max_height = VFE_175_FULL_MAX_HEIGHT,
\t.step_height = 2,
};

'''
s = s[:at]+tables+s[at:]
s = s.replace('#include <linux/limits.h>', '#include <linux/limits.h>\n#include <linux/media-bus-format.h>')
p.write_text(s)
print(git('diff', '--stat'))
