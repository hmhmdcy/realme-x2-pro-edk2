/* Finite provider model, not the kernel control core or a concurrency test.
 * The two sensor entry points and pad-format helper are extracted verbatim.
 * Numeric controls here model range-first mutation and success-only p_cur
 * commit from the inspected source354 V4L2 core, under one held mutex.
 */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <errno.h>
typedef int64_t s64;
#define ARRAY_SIZE(a) (sizeof(a) / sizeof((a)[0]))
#define container_of(p, t, m) ((t *)((char *)(p) - offsetof(t, m)))
#define CCI_REG16(x) (x)
#define V4L2_FIELD_NONE 0
#define V4L2_COLORSPACE_SRGB 1
#define V4L2_YCBCR_ENC_DEFAULT 0
#define V4L2_QUANTIZATION_FULL_RANGE 1
#define V4L2_XFER_FUNC_NONE 0
#define V4L2_SUBDEV_FORMAT_ACTIVE 1
#define V4L2_SUBDEV_FORMAT_TRY 0
enum { V4L2_CID_LINK_FREQ=1, V4L2_CID_PIXEL_RATE, V4L2_CID_HBLANK,
 V4L2_CID_VBLANK, V4L2_CID_EXPOSURE, V4L2_CID_ANALOGUE_GAIN,
 V4L2_CID_TEST_PATTERN, V4L2_CID_HFLIP, V4L2_CID_VFLIP };
struct v4l2_ctrl_handler { int error; };
struct v4l2_ctrl {
 int id, val, cur;
 s64 minimum, maximum, step, default_value;
 struct v4l2_ctrl_handler *handler;
};
struct v4l2_mbus_framefmt {
 unsigned code, width, height, field, colorspace, ycbcr_enc, quantization, xfer_func;
};
struct v4l2_subdev { struct v4l2_ctrl_handler *ctrl_handler; };
struct v4l2_subdev_state { struct v4l2_mbus_framefmt fmt; };
struct v4l2_subdev_format { int which; struct v4l2_mbus_framefmt format; };
struct v4l2_rect { int left, top, width, height; };
struct s5k3m5_mode {
 unsigned width, height, hts, vts, exposure;
 struct v4l2_rect analogue_crop;
};
struct s5k3m5_profile {
 const struct s5k3m5_mode *modes; size_t num_modes; bool clock19_sequence;
};
struct s5k3m5 {
 struct v4l2_ctrl_handler ctrl_handler;
 struct v4l2_subdev sd;
 const struct s5k3m5_profile *profile;
 const struct s5k3m5_mode *mode;
 bool streaming, updating_format, removing, power_fault;
 struct v4l2_ctrl *hblank, *vblank, *exposure;
 void *dev, *regmap;
};
static struct s5k3m5 *to_s5k3m5(struct v4l2_subdev *sd)
{ return container_of(sd, struct s5k3m5, sd); }
static struct v4l2_mbus_framefmt *v4l2_subdev_state_get_format(struct v4l2_subdev_state *s, int pad)
{ assert(pad==0); return &s->fmt; }
static unsigned s5k3m5_get_format_code(struct s5k3m5 *s)
{ (void)s; return 0x300f; }
static const struct s5k3m5_mode *nearest(const struct s5k3m5_mode *m, size_t n, unsigned w, unsigned h)
{
 const struct s5k3m5_mode *best=NULL; uint64_t distance=UINT64_MAX;
 for (size_t i=0; i<n; i++) {
  uint64_t d=(uint64_t)llabs((long long)m[i].width-w)+llabs((long long)m[i].height-h);
  if(d<distance) { distance=d; best=&m[i]; }
 }
 return best;
}
#define v4l2_find_nearest_size(m,n,wf,hf,w,h) nearest(m,n,w,h)
static int pm_calls, pm_puts, writes, powered, write_fail_reg, last_fll, callback_error;
static int api_calls, api_fail_at, api_fail_value, hblank_error;
static int lock_held=1;
static int pm_runtime_get_if_active(void *d)
{ (void)d; assert(lock_held); pm_calls++; return powered; }
static void pm_runtime_put(void *d) { (void)d; pm_puts++; }
static int cci_write(void *r, unsigned reg, int value, void *error)
{
 (void)r; (void)error; writes++;
 if((int)reg==write_fail_reg) return -EIO;
 if(reg==0x0340) last_fll=value;
 return 0;
}
static int s5k3m5_set_ctrl(struct v4l2_ctrl *ctrl);
static int api_inject(void)
{ assert(lock_held); return ++api_calls==api_fail_at ? api_fail_value : 0; }
static bool valid(const struct v4l2_ctrl *c, s64 x)
{ return x>=c->minimum && x<=c->maximum && (x-c->minimum)%c->step==0; }
/* set_ctrl/try_or_set_cluster: callback errors do not commit p_cur, nor set
 * handler.error. This model covers simple, nonvolatile numeric controls. */
static int set_new(struct v4l2_ctrl *c, int x, bool force)
{
 c->val=x;
 if(!valid(c,x)) return -ERANGE;
 if(c->cur==x && !force) return 0;
 int r=s5k3m5_set_ctrl(c);
 if(r) { callback_error=r; if(c->id==V4L2_CID_HBLANK) hblank_error=r; return r; }
 c->cur=c->val;
 return 0;
}
static int __v4l2_ctrl_s_ctrl(struct v4l2_ctrl *c, int x)
{ int r=api_inject(); return r ? r : set_new(c,x,false); }
static int __v4l2_ctrl_modify_range(struct v4l2_ctrl *c, s64 min, s64 max, s64 step, s64 def)
{
 int r=api_inject(); if(r) return r;
 if(step<=0 || min>max || def<min || def>max) return -ERANGE;
 c->minimum=min; c->maximum=max; c->step=step; c->default_value=def;
 c->val=c->cur;
 if(!valid(c,c->cur)) return set_new(c,(int)def,false);
 return 0;
}
