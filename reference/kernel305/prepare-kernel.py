"""Isolate the current kernel commit and repair sensor geometry metadata only."""
from pathlib import Path
import hashlib,json,re,subprocess,urllib.request
import host
HERE=Path(__file__).resolve().parent
base=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
candidate=Path('/home/cy122/x2pro-linux/camera305-sensor-kernel')
assert subprocess.check_output(['git','-C',str(base),'rev-parse','HEAD'],text=True).strip()=='c5e118faec21a6c4bd2e7d5b86b3b21ad9dc2117'
assert not subprocess.check_output(['git','-C',str(base),'status','--porcelain'])
assert not candidate.exists()
url='https://raw.githubusercontent.com/Sr-0w/hotdog-linux-bringup/47087509c4289c2580c54f5433e55366b2e00445/aports/device/testing/linux-oneplus-hotdog-mainline616/0081-media-s5k3m5-report-camera-geometry-and-orientation.patch'
with urllib.request.urlopen(url,timeout=30) as r:reference=r.read()
(host.PRIVATE/'hotdog-geometry-reference-private.patch').write_bytes(reference)
q=subprocess.run(['git','-C',str(base),'worktree','add','--detach',str(candidate),'HEAD'],capture_output=True,timeout=180)
(host.PRIVATE/'worktree-create-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
p=candidate/'drivers/media/i2c/s5k3m5.c';original=p.read_text()
(host.PRIVATE/'s5k3m5-before-private.c').write_text(original)
def replace(s,old,new):
 assert s.count(old)==1,old[:80]
 return s.replace(old,new)
s=replace(original,'\tu32 exposure;\t\t\t/* Default exposure value */','\tu32 exposure;\t\t\t/* Default exposure value */\n\tstruct v4l2_rect analogue_crop;\t/* Relative to the first active pixel */')
s=replace(s,'\t\t.exposure = 256,\n\t\t.reg_list = {\n\t\t\t.regs = s5k3m5_4208x3120_30fps_mode,','\t\t.exposure = 256,\n\t\t.analogue_crop = { 0, 0, 4208, 3120 },\n\t\t.reg_list = {\n\t\t\t.regs = s5k3m5_4208x3120_30fps_mode,')
s=replace(s,'\t\t.exposure = 256,\n\t\t.reg_list = {\n\t\t\t.regs = s5k3m5_2104x1184_60fps_mode,','\t\t.exposure = 256,\n\t\t.analogue_crop = { 0, 376, 4208, 2368 },\n\t\t.reg_list = {\n\t\t\t.regs = s5k3m5_2104x1184_60fps_mode,')
s=replace(s,'{ .width = 2104, .height = 1560, .hts = 9648, .vts = 1663, .exposure = 256,','{ .width = 2104, .height = 1560, .hts = 9648, .vts = 1663, .exposure = 256,\n\t  .analogue_crop = { 0, 0, 4208, 3120 },')
begin=s.index('static int s5k3m5_get_selection(');end=s.index('\nstatic int s5k3m5_init_state(',begin)
s=s[:begin]+'''static int s5k3m5_get_selection(struct v4l2_subdev *sd,
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
                               width, height, format->width, format->height);
  sel->r = mode->analogue_crop;
  return 0;
 default:
  return -EINVAL;
 }
}
''' + s[end:]
p.write_text(s)
q=subprocess.run(['git','-C',str(candidate),'diff','--check'],capture_output=True);assert q.returncode==0,q.stdout.decode()
patch=subprocess.check_output(['git','-C',str(candidate),'diff','--','drivers/media/i2c/s5k3m5.c'])
(HERE/'s5k3m5-geometry.patch').write_bytes(patch)
report=dict(stage=305,base_commit='c5e118faec21a6c4bd2e7d5b86b3b21ad9dc2117',
 existing_solution_url=url,existing_solution_sha256=hashlib.sha256(reference).hexdigest(),
 full_active_size=[4208,3120],coordinate_origin='first active pixel after fixed register margins',
 full_24mhz_crop=[0,0,4208,3120],binned_24mhz_crop=[0,376,4208,2368],binned_19mhz_crop=[0,0,4208,3120],
 source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
 sensor_register_tables_changed=False,soc_driver_changed=False,board_dt_changed=False,
 orientation_not_guessed=True,not_built_or_deployed=True)
(HERE/'kernel-source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
