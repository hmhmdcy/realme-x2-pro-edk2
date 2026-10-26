"""Keep input Bayer dimensions, output bounds and crop negotiation consistent."""
from pathlib import Path
import subprocess

TREE = Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
assert subprocess.check_output(['git','-C',str(TREE),'branch','--show-current'],text=True).strip() == 'samurai-vfe175-pix288'
D = TREE/'drivers/media/platform/qcom/camss'
def change(name, before, after, count=1):
    p=D/name;s=p.read_text();assert s.count(before)==count,(name,s.count(before));p.write_text(s.replace(before,after))
change('camss-vfe.h','\tconst struct v4l2_frmsize_stepwise *pix_frame_sizes;',
'''\tconst struct v4l2_frmsize_stepwise *pix_sink_frame_sizes;
\tconst struct v4l2_frmsize_stepwise *pix_frame_sizes;''')
change('camss-vfe.h','extern const struct v4l2_frmsize_stepwise vfe_frame_sizes_pix_175;',
'''extern const struct v4l2_frmsize_stepwise vfe_frame_sizes_pix_175;
extern const struct v4l2_frmsize_stepwise vfe_frame_sizes_pix_sink_175;''')
change('camss.c','\t\t\t.pix_frame_sizes = &vfe_frame_sizes_pix_175,',
'''\t\t\t.pix_sink_frame_sizes = &vfe_frame_sizes_pix_sink_175,
\t\t\t.pix_frame_sizes = &vfe_frame_sizes_pix_175,''',2)
change('camss-vfe-175-output.c','const struct v4l2_frmsize_stepwise vfe_frame_sizes_pix_175 = {',
'''/* Preserve the common 8191 software ceiling, aligned to Bayer pairs. */
const struct v4l2_frmsize_stepwise vfe_frame_sizes_pix_sink_175 = {
\t.min_width = 16,
\t.max_width = 8190,
\t.step_width = 2,
\t.min_height = 4,
\t.max_height = 8190,
\t.step_height = 2,
};

const struct v4l2_frmsize_stepwise vfe_frame_sizes_pix_175 = {''')
change('camss-vfe.c','''\t\tfmt->height = clamp_t(u32, fmt->height, 1, 8191);

\t\tfmt->field''',
'''\t\tfmt->height = clamp_t(u32, fmt->height, 1, 8191);
\t\tif (line->is_pix && to_vfe(line)->res->pix_sink_frame_sizes) {
\t\t\tconst struct v4l2_frmsize_stepwise *s = to_vfe(line)->res->pix_sink_frame_sizes;

\t\t\tfmt->width = clamp_t(u32, fmt->width, s->min_width, s->max_width);
\t\t\tfmt->height = clamp_t(u32, fmt->height, s->min_height, s->max_height);
\t\t\tfmt->width -= (fmt->width - s->min_width) % s->step_width;
\t\t\tfmt->height -= (fmt->height - s->min_height) % s->step_height;
\t\t}

\t\tfmt->field''')
change('camss-vfe.c','''\t\trect->height -= (rect->height - s->min_height) % s->step_height;
\t}
}

/*
 * vfe_try_crop''',
'''\t\trect->height -= (rect->height - s->min_height) % s->step_height;
\t}
\t/* Compose describes scaling of the full input, not a crop origin. */
\tif (to_vfe(line)->res->pix_no_crop) {
\t\trect->left = 0;
\t\trect->top = 0;
\t}
}

/*
 * vfe_try_crop''')
print('Input/output limits and no-crop negotiation updated.')
