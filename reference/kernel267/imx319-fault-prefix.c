/* Host API outcome model. The real power/stream function bodies follow. */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>
typedef uint8_t u8;typedef uint16_t u16;typedef uint32_t u32;
/* IMX319_DEFINES */
struct imx319_reg { u16 address;u8 val; };
struct imx319_reg_list { u32 num_of_regs;const struct imx319_reg *regs; };
struct imx319_mode { struct imx319_reg_list reg_list; };
struct imx319_profile { const struct imx319_reg_list *global_setting; };
struct imx319;
struct device { struct imx319 *sensor; };
struct v4l2_subdev { struct imx319 *sensor;void *ctrl_handler; };
struct mutex { bool held; };
struct regulator { int role, references; };
struct clk { bool enabled; };
struct gpio_desc { bool asserted; };
struct v4l2_ctrl { bool grabbed; };
struct imx319 {
 struct device *dev;
 struct v4l2_subdev sd;
 struct mutex mutex;
 struct regulator *vana, *vdig, *vif;
 struct clk *clk;
 struct gpio_desc *reset_gpio;
 struct v4l2_ctrl *vflip, *hflip;
 bool managed_power, vana_enabled, vdig_enabled, vif_enabled;
 bool clock_enabled, identified, power_fault, removing, streaming;
 const struct imx319_profile *profile;
 const struct imx319_mode *cur_mode;
};
#define dev_err(dev,...) ((void)(dev))
#define dev_err_ratelimited(dev,...) ((void)(dev))
static struct imx319 *to_imx319(struct v4l2_subdev *sd) { return sd->sensor; }
static void mutex_lock(struct mutex *m) { assert(!m->held);m->held=true; }
static void mutex_unlock(struct mutex *m) { assert(m->held);m->held=false; }
enum operation {
 PIN_DEFAULT, GPIO_ASSERT, EN_VANA, EN_VDIG, EN_VIF, CLOCK_ON,
 GPIO_RELEASE, CLOCK_OFF, DIS_VIF, DIS_VDIG, DIS_VANA, PIN_SLEEP,
 PM_GET, START, STOP, PM_PUT_SYNC, PM_PUT, IDENTIFY, REG_WRITE, CTRL_SETUP, NUM_OPS
};
static unsigned int calls[NUM_OPS], events[4096], event_count;
static int failure_op, failure_at, pm_references, put_sync_error;
static bool persistent, runtime_active, bad_chip_id;
static unsigned int cases;
static int touch(enum operation op) {
 assert(event_count<4096);events[event_count++]=op;calls[op]++;
 return failure_op==(int)op && (calls[op]==(unsigned int)failure_at ||
        (persistent&&calls[op]>=(unsigned int)failure_at)) ? -EIO : 0;
}
static void usleep_range(unsigned int low,unsigned int high) { assert(high>low); }
static int pinctrl_pm_select_default_state(struct device *d) { assert(d);return touch(PIN_DEFAULT); }
static int pinctrl_pm_select_sleep_state(struct device *d) { assert(d);return touch(PIN_SLEEP); }
static int gpiod_set_value_cansleep(struct gpio_desc *g,int value) {
 int ret=touch(value?GPIO_ASSERT:GPIO_RELEASE);if(!ret)g->asserted=value;return ret;
}
static int regulator_enable(struct regulator *r) {
 assert(!r->references);int ret=touch(EN_VANA+r->role);if(!ret)r->references++;return ret;
}
static int regulator_disable(struct regulator *r) {
 assert(r->references==1);int ret=touch(DIS_VANA-r->role);if(!ret)r->references--;return ret;
}
static int clk_prepare_enable(struct clk *c) {
 assert(!c->enabled);int ret=touch(CLOCK_ON);if(!ret)c->enabled=true;return ret;
}
static void clk_disable_unprepare(struct clk *c) { assert(c->enabled);touch(CLOCK_OFF);c->enabled=false; }
static int imx319_power_on(struct imx319 *s);
static int imx319_power_off(struct imx319 *s);
static int pm_runtime_resume_and_get(struct device *d) {
 assert(d->sensor->mutex.held);int ret=touch(PM_GET);if(ret)return ret;
 if(!runtime_active){ret=imx319_power_on(d->sensor);if(ret)return ret;runtime_active=true;}
 pm_references++;return 0;
}
static int pm_runtime_put_sync_suspend(struct device *d) {
 assert(d->sensor->mutex.held&&pm_references==1);touch(PM_PUT_SYNC);pm_references--;
 int ret=imx319_power_off(d->sensor);if(put_sync_error)ret=put_sync_error;
 if(!ret)runtime_active=false;return ret;
}
static int pm_runtime_put(struct device *d) {
 assert(d->sensor->mutex.held&&pm_references==1);touch(PM_PUT);pm_references--;return 0;
}
static int imx319_read_reg(struct imx319 *s,u16 reg,u32 len,u32 *value) {
 assert(s->mutex.held&&pm_references==1&&runtime_active);
 assert(reg==IMX319_REG_CHIP_ID&&len==2);int ret=touch(IDENTIFY);
 if(!ret)*value=bad_chip_id?0xffff:IMX319_CHIP_ID;return ret;
}
static int imx319_write_reg(struct imx319 *s,u16 reg,u32 len,u32 value) {
 assert(s->mutex.held&&pm_references==1&&runtime_active&&s->identified&&len==1);
 if(reg==IMX319_REG_MODE_SELECT)return touch(value==IMX319_MODE_STREAMING?START:STOP);
 return touch(REG_WRITE);
}
static int __v4l2_ctrl_handler_setup(void *handler) {
 struct imx319 *s=handler;assert(s->mutex.held&&pm_references==1&&runtime_active);
 return touch(CTRL_SETUP);
}
static void __v4l2_ctrl_grab(struct v4l2_ctrl *c,int enable) { c->grabbed=enable; }
