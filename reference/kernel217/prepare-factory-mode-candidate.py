"""Prepare an unapplied kernel/DT candidate; full quad RAW needs explicit opt-in."""
from pathlib import Path
import difflib,hashlib,json
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel217');kernel=Path('/home/cy122/pmos-samurai-kernel136/kernel')
assert json.loads((here/'factory-mode-crosscheck-validation.json').read_text())['mode_register_records_verified']==174
modes=json.loads((private/'factory-imx471-modes-private.json').read_text())['modes'];source=kernel/'drivers/media/i2c/imx471.c';old=source.read_text();assert hashlib.sha256(old.encode()).hexdigest()=='cc7562794d1a9b69a0bf7e98f7ed8fcb9e9917b7a6a5c46b833f649a8c60b175';new=old
def replace(before,after):
    global new
    assert new.count(before)==1,before[:100]
    new=new.replace(before,after)
replace('#define IMX471_EXT_CLK\t\t\t\t19200000','#define IMX471_EXT_CLK\t\t\t\t19200000\n\n/* Raw experiment only: full-resolution CFA still needs software remosaic. */\nstatic bool imx471_unprocessed_fullres;\nmodule_param_named(unprocessed_fullres, imx471_unprocessed_fullres, bool, 0444);\nMODULE_PARM_DESC(unprocessed_fullres, "Permit experimental unprocessed full-resolution raw mode");')
replace('\tu32 llp;\n\n\tconst struct cci_reg_sequence *default_mode_regs;','\tu32 llp;\n\tu32 link_freq_index;\n\tu64 pixel_rate;\n\tu32 binning;\n\tstruct v4l2_rect digital_crop;\n\tbool requires_remosaic;\n\n\tconst struct cci_reg_sequence *default_mode_regs;')
replace('\tstruct v4l2_ctrl *exposure;','\tstruct v4l2_ctrl *exposure;\n\tstruct v4l2_ctrl *link_freq;\n\tstruct v4l2_ctrl *pixel_rate;\n\tunsigned long link_freq_bitmap;')
arrays=''
for index,name in [(1,'2304x1728'),(0,'4608x3456')]:
    mode=modes[index];arrays+='\nstatic const struct cci_reg_sequence mode_'+name+'_factory_regs[] = {\n'
    arrays+=''.join('\t{ CCI_REG8(0x%04x), 0x%02x },\n'%(item['address'],item['value']) for item in mode['registers'])+'};\n'
replace('static const s64 link_freq_menu_items[] = {\n\tIMX471_LINK_FREQ_DEFAULT,\n};',arrays+'\nstatic const s64 link_freq_menu_items[] = {\n\tIMX471_LINK_FREQ_DEFAULT,\n\t400000000LL,\n\t748800000LL,\n};')
replace('\t\t.llp = 2328,','\t\t.llp = 2328,\n\t\t.link_freq_index = 0,\n\t\t.pixel_rate = 160000000,\n\t\t.binning = 2,\n\t\t.digital_crop = { 208, 108, 1928, 1088 },')
start=new.index('static const struct imx471_mode imx471_modes[]');end=new.index('\n};',start)
extra=''
for index,name,frequency in [(1,'2304x1728',1),(0,'4608x3456',2)]:
    mode=modes[index];crop=mode['crop'];digital=mode['digital_crop'];minimum=modes[2]['frame_length'] if index==1 else mode['frame_length']
    extra+='\n\t{\n\t\t.width = %d,\n\t\t.height = %d,\n'%(mode['width'],mode['height'])
    extra+='\t\t.crop = { %d, %d, %d, %d },\n'%(crop['left'],crop['top'],crop['right']-crop['left']+1,crop['bottom']-crop['top']+1)
    extra+='\t\t.fll_def = %d,\n\t\t.fll_min = %d,\n\t\t.llp = %d,\n'%(mode['frame_length'],minimum,mode['line_length'])
    extra+='\t\t.link_freq_index = %d,\n\t\t.pixel_rate = %d,\n\t\t.binning = %d,\n'%(frequency,mode['output_pixel_clock_metadata'],mode['binning'][0])
    extra+='\t\t.digital_crop = { %d, %d, %d, %d },\n'%(digital['left'],digital['top'],digital['width'],digital['height'])
    extra+='\t\t.requires_remosaic = %s,\n'%('true' if mode['software_remosaic_required'] else 'false')
    extra+='\t\t.default_mode_regs = mode_%s_factory_regs,\n\t\t.default_mode_regs_length = ARRAY_SIZE(mode_%s_factory_regs),\n\t},'%(name,name)
new=new[:end]+extra+new[end:]
helper='''
static bool imx471_mode_available(const struct imx471 *sensor,
                                  const struct imx471_mode *mode)
{
	return (sensor->link_freq_bitmap & BIT(mode->link_freq_index)) &&
	       (!mode->requires_remosaic || imx471_unprocessed_fullres);
}

static const struct imx471_mode *imx471_find_mode(struct imx471 *sensor,
                                                u32 width, u32 height)
{
	const struct imx471_mode *best = NULL;
	u64 best_distance = U64_MAX;

	for (unsigned int i = 0; i < ARRAY_SIZE(imx471_modes); i++) {
		const struct imx471_mode *mode = &imx471_modes[i];
		u64 distance;

		if (!imx471_mode_available(sensor, mode))
			continue;
		distance = abs((s64)mode->width - width) +
			   abs((s64)mode->height - height);
		if (distance < best_distance) {
			best = mode;
			best_distance = distance;
		}
	}

	return best;
}
'''
replace('static int imx471_get_regulators(struct device *dev, struct imx471 *sensor)',helper+'\nstatic int imx471_get_regulators(struct device *dev, struct imx471 *sensor)')
replace('\tif (ctrl->id == V4L2_CID_VBLANK) {','\t/* Mode metadata controls do not program sensor registers. */\n\tif (ctrl->id == V4L2_CID_LINK_FREQ || ctrl->id == V4L2_CID_PIXEL_RATE)\n\t\treturn 0;\n\n\tif (ctrl->id == V4L2_CID_VBLANK) {')
before='''	if (fse->index >= ARRAY_SIZE(imx471_modes))
		return -EINVAL;

	fse->min_width = imx471_modes[fse->index].width;
	fse->max_width = fse->min_width;
	fse->min_height = imx471_modes[fse->index].height;
	fse->max_height = fse->min_height;

	return 0;'''
after='''	struct imx471 *sensor = to_imx471(sd);
	unsigned int available = 0;

	for (unsigned int i = 0; i < ARRAY_SIZE(imx471_modes); i++) {
		const struct imx471_mode *mode = &imx471_modes[i];

		if (!imx471_mode_available(sensor, mode))
			continue;
		if (available++ != fse->index)
			continue;
		fse->min_width = fse->max_width = mode->width;
		fse->min_height = fse->max_height = mode->height;
		return 0;
	}

	return -EINVAL;'''
replace(before,after)
replace('''	mode = v4l2_find_nearest_size(imx471_modes, ARRAY_SIZE(imx471_modes),
				      width, height, fmt->format.width,
				      fmt->format.height);''','''	mode = imx471_find_mode(sensor, fmt->format.width, fmt->format.height);
	if (!mode)
		return -EINVAL;''')
replace('''	if (fmt->which == V4L2_SUBDEV_FORMAT_TRY)
		return 0;

	ret = __v4l2_ctrl_modify_range(sensor->vblank,''','''	if (fmt->which == V4L2_SUBDEV_FORMAT_TRY)
		return 0;

	ret = __v4l2_ctrl_s_ctrl(sensor->link_freq, mode->link_freq_index);
	if (ret)
		return ret;
	ret = __v4l2_ctrl_modify_range(sensor->pixel_rate, mode->pixel_rate,
				       mode->pixel_rate, 1, mode->pixel_rate);
	if (ret)
		return ret;
	ret = __v4l2_ctrl_s_ctrl_int64(sensor->pixel_rate, mode->pixel_rate);
	if (ret)
		return ret;

	ret = __v4l2_ctrl_modify_range(sensor->vblank,''')
replace('''	h_blank = mode->llp - mode->width;''','''	ret = __v4l2_ctrl_s_ctrl(sensor->vblank, mode->fll_def - mode->height);
	if (ret)
		return ret;

	h_blank = mode->llp - mode->width;''')
replace('''	switch (sel->target) {
	case V4L2_SEL_TGT_CROP:''','''	struct imx471 *sensor = to_imx471(sd);
	struct v4l2_mbus_framefmt *format =
		v4l2_subdev_state_get_format(sd_state, sel->pad);
	const struct imx471_mode *mode =
		imx471_find_mode(sensor, format->width, format->height);

	if (!mode)
		return -EINVAL;

	switch (sel->target) {
	case V4L2_SEL_TGT_COMPOSE:
	case V4L2_SEL_TGT_COMPOSE_DEFAULT:
		sel->r = mode->digital_crop;
		return 0;
	case V4L2_SEL_TGT_COMPOSE_BOUNDS:
		sel->r = (struct v4l2_rect) {
			.width = mode->crop.width / mode->binning,
			.height = mode->crop.height / mode->binning,
		};
		return 0;
	case V4L2_SEL_TGT_CROP:''')
replace('''	case V4L2_SEL_TGT_CROP_DEFAULT:
	case V4L2_SEL_TGT_CROP_BOUNDS:''','''	case V4L2_SEL_TGT_CROP_BOUNDS:
		sel->r = (struct v4l2_rect) {
			.width = IMX471_NATIVE_WIDTH,
			.height = IMX471_NATIVE_HEIGHT,
		};
		return 0;
	case V4L2_SEL_TGT_CROP_DEFAULT:''')
replace('''	mode = v4l2_find_nearest_size(imx471_modes, ARRAY_SIZE(imx471_modes),
				      width, height, fmt->width, fmt->height);''','''	mode = imx471_find_mode(sensor, fmt->width, fmt->height);
	if (!mode) {
		ret = -EINVAL;
		goto error_powerdown;
	}
	if (mode->requires_remosaic)
		dev_warn_once(sensor->dev, "Full-resolution stream requires software remosaic\\n");''')
replace('''	/* pixel_rate = link_freq * 2 * nr_of_lanes / bits_per_sample */''','''	sensor->link_freq = link_freq;
	link_freq->menu_skip_mask = GENMASK(ARRAY_SIZE(link_freq_menu_items) - 1, 0) &
				    ~sensor->link_freq_bitmap;

	/* pixel_rate = link_freq * 2 * nr_of_lanes / bits_per_sample */''')
replace('''	v4l2_ctrl_new_std(ctrl_hdlr, &imx471_ctrl_ops,
			  V4L2_CID_PIXEL_RATE, pixel_rate,''','''	sensor->pixel_rate = v4l2_ctrl_new_std(ctrl_hdlr, &imx471_ctrl_ops,
			  V4L2_CID_PIXEL_RATE, pixel_rate,''')
replace('''				       &link_freq_bitmap);

done_endpoint_free:''','''				       &link_freq_bitmap);
	if (!ret) {
		/* Preserve the legacy default mode while adding opt-in profiles. */
		if (!(link_freq_bitmap & BIT(0)))
			ret = -EINVAL;
		else
			sensor->link_freq_bitmap = link_freq_bitmap;
	}

done_endpoint_free:''')
candidate=private/'candidate-source';candidate.mkdir(mode=0o700);(candidate/'imx471.c').write_text(new)
board=kernel/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts';old_board=board.read_text();needle='link-frequencies = /bits/ 64 <200000000>;';assert old_board.count(needle)==1
new_board=old_board.replace(needle,'link-frequencies = /bits/ 64 <200000000 400000000 748800000>;');(candidate/'sm8150-samurai.dts').write_text(new_board)
patch=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/drivers/media/i2c/imx471.c',tofile='b/drivers/media/i2c/imx471.c'))
patch+=''.join(difflib.unified_diff(old_board.splitlines(True),new_board.splitlines(True),fromfile='a/arch/arm64/boot/dts/qcom/sm8150-samurai.dts',tofile='b/arch/arm64/boot/dts/qcom/sm8150-samurai.dts'))
(here/'imx471-factory-modes-candidate.patch').write_text(patch)
report=dict(stage=217,candidate_only_not_applied_to_running_or_canonical_sources=True,source_sha256=hashlib.sha256(new.encode()).hexdigest(),board_sha256=hashlib.sha256(new_board.encode()).hexdigest(),legacy_preview_registers_preserved=True,profiles=['1928x1088 legacy','2304x1728 factory30 with lower vblank supporting factory60','4608x3456 unprocessed software-remosaic raw experiment'],mode_availability_honours_firmware_link_frequencies=True,full_unprocessed_mode_requires_explicit_module_opt_in=True,full_rgb_or_remosaic_not_implemented=True,compose_geometry_and_link_pixel_control_switching_added=True,external_clock_and_power_sequences_unchanged=True,proposed_link_frequencies=[200000000,400000000,748800000],new_clock_values_from_factory_op_pll_and_output_clock_metadata=True,frame_timing_accuracy_not_yet_accepted=True,build_and_physical_validation_pending=True)
(here/'factory-mode-candidate-source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
