/* Mode descriptors come from the candidate being reviewed, not this file. */
static struct s5k3m5 sensor;
static struct v4l2_ctrl controls[10];
static struct v4l2_subdev_state active;
static struct s5k3m5_profile profile;
static int tests;
#define CHECK(x) do { if(!(x)) { fprintf(stderr,"line %d: %s\n",__LINE__,#x); exit(1); } } while(0)
static void clear_observations(void)
{
 pm_calls=pm_puts=writes=last_fll=callback_error=api_calls=hblank_error=0;
 api_fail_at=0; api_fail_value=-EIO; write_fail_reg=-1;
}
static void init_control(int id, int min, int max, int value)
{
 controls[id]=(struct v4l2_ctrl){.id=id,.val=value,.cur=value,.minimum=min,
  .maximum=max,.step=1,.default_value=value,.handler=&sensor.ctrl_handler};
}
static void reset_profile(const struct s5k3m5_mode *modes, size_t count, bool clock19, unsigned mode_index)
{
 memset(&sensor,0,sizeof(sensor)); memset(controls,0,sizeof(controls));
 profile=(struct s5k3m5_profile){modes,count,clock19};
 sensor.sd.ctrl_handler=&sensor.ctrl_handler;
 sensor.profile=&profile; sensor.mode=&modes[mode_index];
 const struct s5k3m5_mode *m=sensor.mode;
 sensor.hblank=&controls[V4L2_CID_HBLANK]; sensor.vblank=&controls[V4L2_CID_VBLANK];
 sensor.exposure=&controls[V4L2_CID_EXPOSURE];
 init_control(V4L2_CID_HBLANK,m->hts-m->width,m->hts-m->width,m->hts-m->width);
 init_control(V4L2_CID_VBLANK,m->vts-m->height,65535-m->height,m->vts-m->height);
 init_control(V4L2_CID_EXPOSURE,clock19?1:8,m->vts-4,m->exposure);
 init_control(V4L2_CID_LINK_FREQ,0,0,0);
 init_control(V4L2_CID_PIXEL_RATE,0,481930000,481930000);
 s5k3m5_update_pad_format(&sensor,m,&active.fmt);
 powered=1; clear_observations();
}
static void reset(unsigned mode_index)
{ reset_profile(review_modes,ARRAY_SIZE(review_modes),true,mode_index); }
static int change(unsigned index, int which, struct v4l2_subdev_state *state)
{
 struct v4l2_subdev_format f={.which=which,.format={.width=sensor.profile->modes[index].width,.height=sensor.profile->modes[index].height}};
 return s5k3m5_set_pad_format(&sensor.sd,state,&f);
}
static void controls_match(unsigned index)
{
 const struct s5k3m5_mode *m=&sensor.profile->modes[index];
 CHECK(sensor.mode==m); CHECK(active.fmt.width==m->width && active.fmt.height==m->height);
 CHECK(sensor.hblank->cur==(int)(m->hts-m->width));
 CHECK(sensor.hblank->minimum==sensor.hblank->maximum && sensor.hblank->maximum==sensor.hblank->cur);
 CHECK(sensor.vblank->minimum==m->vts-m->height && sensor.vblank->maximum==65535-m->height);
 CHECK(sensor.vblank->cur==(int)(m->vts-m->height));
 CHECK(sensor.exposure->minimum==(sensor.profile->clock19_sequence?1:8) && sensor.exposure->maximum==m->vts-4);
 CHECK(sensor.exposure->cur==(int)m->exposure);
 CHECK(!sensor.updating_format);
}
static int handler_setup_model(void)
{
 /* The inspected enable_streams writes its selected mode table first, then
  * __handler_setup, before streaming=true. Force callbacks as core setup does. */
 /* Read-only metadata is skipped; exercise the two timing controls. */
 const int ids[]={V4L2_CID_VBLANK,V4L2_CID_EXPOSURE};
 for(size_t i=0;i<ARRAY_SIZE(ids);i++) {
  int r=set_new(&controls[ids[i]],controls[ids[i]].cur,true); if(r)return r;
 }
 return 0;
}
int main(void)
{
#ifdef REVIEW_BASELINE
 reset(0); CHECK(change(1,V4L2_SUBDEV_FORMAT_ACTIVE,&active)==0);
 CHECK(hblank_error==-EINVAL); CHECK(callback_error==-EINVAL);
 CHECK(sensor.ctrl_handler.error==0); CHECK(last_fll==2504);
 printf("{\"baseline_hblank_einval_ignored\":true,\"baseline_old_height_fll\":%d,\"expected_fll\":3312}\n",last_fll);
#else
 /* Both profiles, all four finite descriptors: every new range's static
  * default is valid; legacy profile also keeps the cache-only format path. */
 for(unsigned clock19=0;clock19<2;clock19++) for(unsigned index=0;index<2;index++) {
  const struct s5k3m5_mode *modes=clock19?review_modes:legacy_modes;
  reset_profile(modes,2,clock19,index);
  CHECK(sensor.hblank->step==1 && valid(sensor.hblank,sensor.hblank->default_value));
  CHECK(sensor.vblank->step==1 && valid(sensor.vblank,sensor.vblank->default_value));
  CHECK(sensor.exposure->step==1 && valid(sensor.exposure,sensor.exposure->default_value));
  CHECK(change(1-index,V4L2_SUBDEV_FORMAT_ACTIVE,&active)==0);
  controls_match(1-index); CHECK(pm_calls==0 && writes==0); tests++;
 }
 /* Powered-idle, both directions, including metadata callbacks. */
 for(unsigned from=0;from<2;from++) {
  reset(from); CHECK(change(1-from,V4L2_SUBDEV_FORMAT_ACTIVE,&active)==0);
  controls_match(1-from); CHECK(pm_calls==0 && pm_puts==0 && writes==0); tests++;
 }
 reset(0); struct v4l2_subdev_state trial=active;
 CHECK(change(1,V4L2_SUBDEV_FORMAT_TRY,&trial)==0);
 controls_match(0); CHECK(trial.fmt.width==4208 && trial.fmt.height==2368);
 CHECK(api_calls==0 && pm_calls==0 && writes==0); tests++;
 sensor.streaming=true; struct v4l2_subdev_state before=active;
 CHECK(change(1,V4L2_SUBDEV_FORMAT_ACTIVE,&active)==-EBUSY);
 CHECK(memcmp(&before,&active,sizeof(active))==0); controls_match(0);
 CHECK(api_calls==0 && pm_calls==0 && writes==0); tests++;
 reset(1); CHECK(change(1,V4L2_SUBDEV_FORMAT_ACTIVE,&active)==0);
 controls_match(1); CHECK(api_calls==0 && pm_calls==0 && writes==0); tests++;
 reset(0); CHECK(change(1,V4L2_SUBDEV_FORMAT_ACTIVE,&active)==0);
 clear_observations(); CHECK(handler_setup_model()==0);
 CHECK(last_fll==3312 && pm_calls==2 && pm_puts==2 && writes==2); tests++;
 clear_observations(); write_fail_reg=S5K3M5_REG_VTS;
 CHECK(handler_setup_model()==-EIO); CHECK(writes==1 && pm_calls==1 && pm_puts==1); tests++;
 clear_observations(); CHECK(__v4l2_ctrl_s_ctrl(sensor.vblank,1500)==0);
 CHECK(last_fll==3868 && pm_calls==1 && writes==1 && sensor.exposure->maximum==3864); tests++;
 CHECK(__v4l2_ctrl_s_ctrl(sensor.exposure,3800)==0);
 clear_observations(); write_fail_reg=S5K3M5_REG_EXPOSURE;
 CHECK(__v4l2_ctrl_s_ctrl(sensor.vblank,944)==-EIO);
 CHECK(sensor.vblank->cur==1500 && sensor.exposure->cur==3800);
 CHECK(sensor.exposure->maximum==3308); /* range changed, no fictitious rollback */
 CHECK(last_fll==0 && writes==1 && pm_calls==1 && pm_puts==1 && sensor.ctrl_handler.error==0); tests++;
 reset(1); powered=0; CHECK(__v4l2_ctrl_s_ctrl(sensor.vblank,1500)==0);
 CHECK(pm_calls==1 && writes==0 && sensor.exposure->maximum==3864); tests++;
 reset(1); sensor.power_fault=true;
 CHECK(__v4l2_ctrl_s_ctrl(sensor.exposure,257)==-EIO); CHECK(pm_calls==0 && writes==0); tests++;
 reset(1); clear_observations();
 CHECK(s5k3m5_set_ctrl(&controls[V4L2_CID_HBLANK])==0);
 CHECK(s5k3m5_set_ctrl(&controls[V4L2_CID_PIXEL_RATE])==0);
 CHECK(s5k3m5_set_ctrl(&controls[V4L2_CID_LINK_FREQ])==0);
 CHECK(pm_calls==0 && writes==0); tests++;
 /* Fail each API invocation on both paths, including nested range updates.
  * Injected failures supplement the real nested I2C failure above. */
 for(unsigned from=0;from<2;from++) {
  reset(from); CHECK(change(1-from,V4L2_SUBDEV_FORMAT_ACTIVE,&active)==0);
  int calls=api_calls;
  for(int fail=1;fail<=calls;fail++) {
   reset(from); api_fail_at=fail;
   CHECK(change(1-from,V4L2_SUBDEV_FORMAT_ACTIVE,&active)==-EIO);
   CHECK(!sensor.updating_format && sensor.mode==&review_modes[1-from]);
   CHECK(active.fmt.width==sensor.mode->width && active.fmt.height==sensor.mode->height);
   CHECK(pm_calls==0 && writes==0 && sensor.ctrl_handler.error==0); tests++;
  }
 }
 printf("{\"candidate_cases\":%d,\"passed\":true,\"finite_provider_model\":true,\"kernel_concurrency_test\":false}\n",tests);
#endif
 return 0;
}
