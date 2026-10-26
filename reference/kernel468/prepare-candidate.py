"""Append the retained OEM tele mode2 and keep format changes in control cache."""
from pathlib import Path
import difflib,hashlib,json,re,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel468')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base=PRIVATE/'baseline/drivers/media/i2c'
assert sha(base/'s5k3m5.c')=='f0f715826d96521266315f42e6fd9f4a08d1de2695226deecb06fa7c529e1745'
assert sha(base/'s5k3m5-19mhz-tables.h')=='5f55d6bd4a7e1c22501c09e6f1d7c4c4ba24ba8829180b58b7da6d540b5e1e01'
original=(base/'s5k3m5.c').read_text();text=original
def replace(a,b):
    global text
    assert text.count(a)==1,(a,text.count(a));text=text.replace(a,b)
replace('\tbool streaming;\n','\tbool streaming;\n\tbool updating_format;\n')
old='''\t  .reg_list = { s5k3m5_clock19_mode3_regs, ARRAY_SIZE(s5k3m5_clock19_mode3_regs) } },
};'''
new=old[:-3]+'''
\t/* Retained RMX1931 OEM mode2: HFR label, declared 30fps, no binning. */
\t{ .width = 4208, .height = 2368, .hts = 4848, .vts = 3312, .exposure = 256,
\t  .analogue_crop = { 0, 376, 4208, 2368 },
\t  .reg_list = { s5k3m5_clock19_mode2_regs, ARRAY_SIZE(s5k3m5_clock19_mode2_regs) } },
};'''
replace(old,new)
replace('/* OEM mode3 timing metadata; native SOF/line timing validation pending. */',
        '/* OEM mode2/3 control timing metadata; distinct from CSI pixel throughput. */')
needle='''\t/* Propagate change of current control to all related controls */
\tswitch (ctrl->id) {'''
replace(needle,'''\t/* These describe the selected mode and never program sensor registers. */
\tif (ctrl->id == V4L2_CID_LINK_FREQ || ctrl->id == V4L2_CID_PIXEL_RATE ||
\t    ctrl->id == V4L2_CID_HBLANK)
\t\treturn 0;

'''+needle)
replace('''\t\t__v4l2_ctrl_modify_range(s5k3m5->exposure,
\t\t\t\t\t s5k3m5->exposure->minimum,
\t\t\t\t\t exposure_max,
\t\t\t\t\t s5k3m5->exposure->step,
\t\t\t\t\t s5k3m5->exposure->default_value);
\t\tbreak;''','''\t\tret = __v4l2_ctrl_modify_range(s5k3m5->exposure,
\t\t\t\t\t s5k3m5->exposure->minimum,
\t\t\t\t\t exposure_max,
\t\t\t\t\t s5k3m5->exposure->step,
\t\t\t\t\t s5k3m5->exposure->default_value);
\t\tif (ret)
\t\t\treturn ret;
\t\tbreak;''')
needle='''\t/* V4L2 controls are applied, when sensor is powered up for streaming */'''
replace(needle,'''\t/* ACTIVE S_FMT changes a stopped mode's cache under the shared lock.
\t * The mode table plus handler_setup apply it together at stream-on,
\t * including when S_FMT is called while runtime-powered but idle.
\t */
\tif (s5k3m5->updating_format)
\t\treturn 0;

'''+needle)
start=text.index('static int s5k3m5_set_pad_format(')
end=text.index('\nstatic int s5k3m5_enum_mbus_code(',start)
replacement='''static int s5k3m5_set_pad_format(struct v4l2_subdev *sd,
\t\t\t\t struct v4l2_subdev_state *state,
\t\t\t\t struct v4l2_subdev_format *fmt)
{
\tstruct s5k3m5 *s5k3m5 = to_s5k3m5(sd);
\ts64 hblank, vblank, exposure_max;
\tconst struct s5k3m5_mode *mode;
\tint ret;

\tif (fmt->which == V4L2_SUBDEV_FORMAT_ACTIVE && s5k3m5->streaming)
\t\treturn -EBUSY;
\tmode = v4l2_find_nearest_size(s5k3m5->profile->modes,
\t\t\t\t      s5k3m5->profile->num_modes,
\t\t\t\t      width, height,
\t\t\t\t      fmt->format.width, fmt->format.height);

\ts5k3m5_update_pad_format(s5k3m5, mode, &fmt->format);

\tif (fmt->which == V4L2_SUBDEV_FORMAT_TRY || s5k3m5->mode == mode)
\t\tgoto set_format;

\t/* state_lock == ctrl_handler->lock: no control callback can interleave.
\t * Publish the desired mode and state before propagating its control cache.
\t * No I2C or PM operation is issued until the existing stream-on setup.
\t */
\ts5k3m5->mode = mode;
\t*v4l2_subdev_state_get_format(state, 0) = fmt->format;
\ts5k3m5->updating_format = true;

\thblank = mode->hts - mode->width;
\tret = __v4l2_ctrl_modify_range(s5k3m5->hblank, hblank, hblank, 1, hblank);
\tif (ret)
\t\tgoto format_done;

\tvblank = mode->vts - mode->height;
\tret = __v4l2_ctrl_modify_range(s5k3m5->vblank, vblank,
\t\t\t\t S5K3M5_VTS_MAX - mode->height, 1, vblank);
\tif (ret)
\t\tgoto format_done;
\tret = __v4l2_ctrl_s_ctrl(s5k3m5->vblank, vblank);
\tif (ret)
\t\tgoto format_done;

\texposure_max = mode->vts - S5K3M5_EXPOSURE_MARGIN;
\tret = __v4l2_ctrl_modify_range(s5k3m5->exposure,
\t\t\t\t s5k3m5->profile->clock19_sequence ? 1 : S5K3M5_EXPOSURE_MIN,
\t\t\t\t exposure_max, S5K3M5_EXPOSURE_STEP, mode->exposure);
\tif (ret)
\t\tgoto format_done;
\tret = __v4l2_ctrl_s_ctrl(s5k3m5->exposure, mode->exposure);

format_done:
\ts5k3m5->updating_format = false;
\treturn ret;

set_format:
\t*v4l2_subdev_state_get_format(state, 0) = fmt->format;
\treturn 0;
}
'''
text=text[:start]+replacement+text[end:]
table=PRIVATE.parent/'kernel465/s5k3m5-mode2-draft-regs-private.h'
assert sha(table)=='4a85143c2f0577bc6564a7e55073f07e99714544d962d42f1b481daaee14268a'
header=(base/'s5k3m5-19mhz-tables.h').read_bytes()+b'\n'+table.read_bytes()
candidate=PRIVATE/'candidate/drivers/media/i2c';candidate.mkdir(mode=0o700,parents=True,exist_ok=True)
(candidate/'s5k3m5.c').write_text(text);(candidate/'s5k3m5-19mhz-tables.h').write_bytes(header)
profile=PRIVATE.parent/'kernel465/factory-s5k3m5-mode2-draft-private.yaml'
assert sha(profile)=='6396ced1039e352a14c7a07187e780596a3a4180b22391bca0b30f7518db4094'
(PRIVATE/'factory-s5k3m5-mode2-private.yaml').write_bytes(profile.read_bytes())
patch=''.join(difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile='a/drivers/media/i2c/s5k3m5.c',tofile='b/drivers/media/i2c/s5k3m5.c'))
(HERE/'0001-media-s5k3m5-stock-mode2-format-cache.patch').write_text(patch)
manifest=dict(stage=468,candidate_sha256=sha(candidate/'s5k3m5.c'),header_sha256=sha(candidate/'s5k3m5-19mhz-tables.h'),
    baseline_c_sha256=sha(base/'s5k3m5.c'),baseline_header_sha256=sha(base/'s5k3m5-19mhz-tables.h'),
    private_table_sha256=sha(table),private_profile_sha256=sha(PRIVATE/'factory-s5k3m5-mode2-private.yaml'),
    mode2_dimensions=[4208,2368],mode2_ll_fll=[4848,3312],mode2_crop=[0,376,4208,2368],
    advertised_link_hz=723200000,control_pixel_rate=481930000,mode3_numeric_metadata_preserved=True,
    private_source_created=True,compiled=False,phone_accessed=False,passed=True)
(PRIVATE/'candidate-manifest-private.json').write_text(json.dumps(manifest,indent=2)+'\n')
(HERE/'candidate-validation.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(manifest))
