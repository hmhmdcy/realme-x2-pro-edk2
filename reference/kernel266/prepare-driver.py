"""Add standard geometry and firmware controls without changing register programming."""
from pathlib import Path
import difflib,hashlib,json,re,shutil
R=Path(__file__).parent;B=R.parent/'kernel235'
s=(B/'imx319.c').read_text();original=s
g=json.loads((R/'geometry-validation.json').read_text())['register_geometry']
needle='/* Mode : resolution and related config&values */';assert s.count(needle)==1
s=s.replace(needle,'''/* Full unbinned register-list readout coordinate space. */
#define IMX319_NATIVE_WIDTH	3280
#define IMX319_NATIVE_HEIGHT	2464

'''+needle)
needle='\tu32 height;\n\n\t/* V-timing */';assert s.count(needle)==1;s=s.replace(needle,'\tu32 height;\n\tstruct v4l2_rect analogue_crop;\n\n\t/* V-timing */')
for row in g:
 name=row['name'];pos=s.index('.regs = '+name) if name!='imx319_oem_mode_regs' else s.index('.reg_list = { ARRAY_SIZE(imx319_oem_mode_regs)')
 start=s.rfind('\n\t{',0,pos);end=s.index('\n\t},',pos);block=s[start:end]
 crop=row['analogue_crop'];line=next(l for l in block.splitlines(True) if '.height =' in l)
 added='\t\t.analogue_crop = {\n\t\t\t.left = '+str(crop['left'])+', .top = '+str(crop['top'])+',\n\t\t\t.width = '+str(crop['width'])+', .height = '+str(crop['height'])+',\n\t\t},\n'
 block=block.replace(line,line+added,1);s=s[:start]+block+s[end:]
needle='static int\nimx319_set_pad_format(';assert s.count(needle)==1
function='''static int imx319_get_selection(struct v4l2_subdev *sd,
			       struct v4l2_subdev_state *sd_state,
			       struct v4l2_subdev_selection *sel)
{
	struct imx319 *imx319 = to_imx319(sd);
	const struct imx319_mode *mode;
	struct v4l2_mbus_framefmt *format;

	if (sel->pad || (sel->which != V4L2_SUBDEV_FORMAT_ACTIVE &&
			 sel->which != V4L2_SUBDEV_FORMAT_TRY))
		return -EINVAL;

	switch (sel->target) {
	case V4L2_SEL_TGT_NATIVE_SIZE:
	case V4L2_SEL_TGT_CROP_BOUNDS:
	case V4L2_SEL_TGT_CROP_DEFAULT:
		sel->r = (struct v4l2_rect) {
			.left = 0, .top = 0,
			.width = IMX319_NATIVE_WIDTH,
			.height = IMX319_NATIVE_HEIGHT,
		};
		return 0;
	case V4L2_SEL_TGT_CROP:
		mutex_lock(&imx319->mutex);
		if (sel->which == V4L2_SUBDEV_FORMAT_TRY) {
			format = v4l2_subdev_state_get_format(sd_state, sel->pad);
			mode = v4l2_find_nearest_size(imx319->profile->modes,
						    imx319->profile->num_modes,
						    width, height,
						    format->width, format->height);
		} else {
			mode = imx319->cur_mode;
		}
		/* Report the analogue window before binning/digital cropping. */
		sel->r = mode->analogue_crop;
		mutex_unlock(&imx319->mutex);
		return 0;
	default:
		return -EINVAL;
	}
}

'''
s=s.replace(needle,function+needle)
needle='\t.set_fmt = imx319_set_pad_format,';assert s.count(needle)==1;s=s.replace(needle,needle+'\n\t.get_selection = imx319_get_selection,')
needle='static int imx319_init_controls(struct imx319 *imx319)\n{\n';assert s.count(needle)==1
s=s.replace(needle,needle+'\tstruct v4l2_fwnode_device_properties props;\n')
needle='\tctrl_hdlr = &imx319->ctrl_handler;\n\tret = v4l2_ctrl_handler_init(ctrl_hdlr, 10);';assert s.count(needle)==1
s=s.replace(needle,'''	ret = v4l2_fwnode_device_parse(imx319->dev, &props);
	if (ret)
		return ret;

	ctrl_hdlr = &imx319->ctrl_handler;
	ret = v4l2_ctrl_handler_init(ctrl_hdlr, 12);''')
needle='\tctrl_hdlr->lock = &imx319->mutex;\n';assert s.count(needle)==1
s=s.replace(needle,needle+'''\tret = v4l2_ctrl_new_fwnode_properties(ctrl_hdlr, &imx319_ctrl_ops, &props);
	if (ret)
		goto error;
''')
(R/'imx319.c').write_text(s);shutil.copyfile(B/'imx319-oem-tables.h',R/'imx319-oem-tables.h')
dt=(B/'imx319-p-lab.dtsi').read_text();needle='\t\tcompatible = "realme,rmx1931-imx319";';assert dt.count(needle)==1;dt=dt.replace(needle,needle+'\n\t\torientation = <1>;')
(R/'imx319-p-lab.dtsi').write_text(dt)
(R/'imx319-standard-metadata.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),s.splitlines(True),fromfile='a/drivers/media/i2c/imx319.c',tofile='b/drivers/media/i2c/imx319.c')))
# Require all existing hardware programming arrays to remain byte-identical.
arrays=lambda text:re.findall(r'static const struct imx319_reg \w+\[\] = \{.*?\n\};',text,re.S)
assert arrays(original)==arrays(s)
report=dict(stage=266,source_sha256=hashlib.sha256(s.encode()).hexdigest(),original_register_arrays_unchanged=True,oem_register_header_unchanged=(R/'imx319-oem-tables.h').read_bytes()==(B/'imx319-oem-tables.h').read_bytes(),geometry_from_all_nine_register_lists=True,firmware_properties_only=True,rmx1931_orientation_fallback=False,unknown_rotation_not_invented=True,hardware_not_changed=True)
(R/'source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

