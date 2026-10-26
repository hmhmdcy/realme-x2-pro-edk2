"""Use kernel indentation without changing the reviewed geometry."""
from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent
TREE=Path('/home/cy122/x2pro-linux/camera305-sensor-kernel')
p=TREE/'drivers/media/i2c/s5k3m5.c'
text=p.read_text();begin=text.index('static int s5k3m5_get_selection(');end=text.index('\nstatic int s5k3m5_init_state(',begin)
callback='''static int s5k3m5_get_selection(struct v4l2_subdev *sd,
			      struct v4l2_subdev_state *sd_state,
			      struct v4l2_subdev_selection *sel)
{
	struct s5k3m5 *s5k3m5 = to_s5k3m5(sd);
	const struct s5k3m5_mode *mode;
	struct v4l2_mbus_framefmt *format;

	if (sel->pad || (sel->which != V4L2_SUBDEV_FORMAT_ACTIVE &&
			sel->which != V4L2_SUBDEV_FORMAT_TRY))
		return -EINVAL;

	/* Coordinates start at the first active pixel, after the fixed margins. */
	switch (sel->target) {
	case V4L2_SEL_TGT_NATIVE_SIZE:
	case V4L2_SEL_TGT_CROP_BOUNDS:
	case V4L2_SEL_TGT_CROP_DEFAULT:
		sel->r = (struct v4l2_rect) { 0, 0, 4208, 3120 };
		return 0;
	case V4L2_SEL_TGT_CROP:
		format = v4l2_subdev_state_get_format(sd_state, sel->pad);
		mode = v4l2_find_nearest_size(s5k3m5->profile->modes,
					    s5k3m5->profile->num_modes,
					    width, height,
					    format->width, format->height);
		sel->r = mode->analogue_crop;
		return 0;
	default:
		return -EINVAL;
	}
}
'''
p.write_text(text[:begin]+callback+text[end:])
subprocess.run(['git','-C',str(TREE),'diff','--check'],check=True)
(HERE/'s5k3m5-geometry.patch').write_bytes(subprocess.check_output(['git','-C',str(TREE),'diff','--','drivers/media/i2c/s5k3m5.c']))
report=json.loads((HERE/'kernel-source-validation.json').read_text())
report['source_sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
(HERE/'kernel-source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(report['source_sha256'])
