/* Real functions extracted from the driver; hardware and IRQ waits are stubs. */
#include <assert.h>
#include <errno.h>
#include <pthread.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define READ_ONCE(x) __atomic_load_n(&(x),__ATOMIC_SEQ_CST)
#define WRITE_ONCE(x,v) __atomic_store_n(&(x),(v),__ATOMIC_SEQ_CST)
#define EXPORT_SYMBOL(x)
#define EXPORT_SYMBOL_GPL(x)
#define DRM_MODE_CONNECTOR_Unknown 0
#define FB_BLANK_POWERDOWN 4
#define container_of(p,t,m) ((t *)((char *)(p)-offsetof(t,m)))
#define DRM_WARN(...) ((void)0)
#define DRM_DEV_INFO(...) ((void)0)
#define DPU_ERROR(...) ((void)0)
#define DRMID(p) (1)
#define dev_warn(...) ((void)0)
#define dev_info(...) ((void)0)
struct device {const char *name;};
struct drm_panel;
struct drm_panel_follower;
struct list_head {struct drm_panel_follower *one;};
#define INIT_LIST_HEAD(p) ((p)->one=NULL)
#define list_for_each_entry(p,h,m) for((p)=(h)->one;(p);(p)=NULL)
struct backlight_device {struct {int brightness,power;} props;void *data;};
struct drm_panel_funcs {int (*enable)(struct drm_panel *);int (*disable)(struct drm_panel *);};
struct follower_funcs {int (*panel_enabled)(struct drm_panel_follower *);int (*panel_disabling)(struct drm_panel_follower *);};
struct drm_panel_follower {struct follower_funcs *funcs;};
struct drm_panel {struct device *dev;const struct drm_panel_funcs *funcs;
    struct backlight_device *backlight;struct list_head list,followers;
    pthread_mutex_t follower_lock;int connector_type;
    bool prepared,enabled,delay_backlight_until_first_frame,backlight_ready;};
struct mipi_dsi_device {int dummy;};
struct sofef03f {struct drm_panel panel;struct mipi_dsi_device *dsi;};
struct drm_bridge {bool panel_bridge;struct drm_bridge *next;};
struct panel_bridge {struct drm_bridge bridge;struct drm_panel *panel;};
struct drm_encoder {struct drm_bridge *bridge;};
struct drm_device {struct drm_encoder *encoder;};
struct drm_crtc_state {bool enable,active;unsigned encoder_mask;};
struct drm_crtc {struct drm_device *dev;struct drm_crtc_state *state;};
#define drm_for_each_encoder_mask(e,d,m) for((e)=((m)&1)?(d)->encoder:NULL;(e);(e)=NULL)
#define drm_for_each_bridge_in_chain(e,b) for(struct drm_bridge *b=(e)->bridge;(b);(b)=(b)->next)
static __attribute__((unused)) bool drm_bridge_is_panel(const struct drm_bridge *b) {return b->panel_bridge;}
static __attribute__((unused)) struct panel_bridge *drm_bridge_to_panel_bridge(struct drm_bridge *b) {return container_of(b,struct panel_bridge,bridge);}
static __attribute__((unused)) bool drm_atomic_crtc_effectively_active(struct drm_crtc_state *s) {return s->active;}
static __attribute__((unused)) const char *dev_name(struct device *d) {return d->name;}
static void mutex_init(pthread_mutex_t *m) {assert(!pthread_mutex_init(m,NULL));}
static void mutex_lock(pthread_mutex_t *m) {assert(!pthread_mutex_lock(m));}
static void mutex_unlock(pthread_mutex_t *m) {assert(!pthread_mutex_unlock(m));}
static struct sofef03f ctx;
static struct backlight_device bl;
static struct mipi_dsi_device dsi;
static int writes,positive_writes,physical_brightness,premature,unclocked,followers_on,followers_off;
static int enable_failure,tx_return,tx_waits,trace_pending,trace_ready;
static bool clocks_on,tx_done,fixture_ready;
static pthread_mutex_t tx_lock=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t tx_cond=PTHREAD_COND_INITIALIZER;
static bool block_tx,waiting,release_tx;
static void *bl_get_data(struct backlight_device *p) {return p->data;}
static int backlight_get_brightness(struct backlight_device *p) {return p->props.power?0:p->props.brightness;}
static int mipi_dsi_dcs_set_display_brightness_large(struct mipi_dsi_device *p,int level) {
    assert(p==&dsi);writes++;positive_writes+=level>0;physical_brightness=level;
    unclocked+=!clocks_on;premature+=level>0&&ctx.panel.delay_backlight_until_first_frame&&!tx_done;
    return 0;
}
static int sofef03f_bl_update(struct backlight_device *);
static int backlight_enable(struct backlight_device *p) {if(!p)return 0;p->props.power=0;return sofef03f_bl_update(p);}
static int backlight_disable(struct backlight_device *p) {if(!p)return 0;p->props.power=4;return sofef03f_bl_update(p);}
static int fake_enable(struct drm_panel *p) {(void)p;return enable_failure;}
static int fake_disable(struct drm_panel *p) {(void)p;return 0;}
static int follower_enable(struct drm_panel_follower *p) {(void)p;followers_on++;return 0;}
static int follower_disable(struct drm_panel_follower *p) {(void)p;followers_off++;return 0;}
static __attribute__((unused)) void trace_drm_panel_backlight(const char *name,int phase,int brightness) {
    (void)name;(void)brightness;trace_pending+=phase==0;trace_ready+=phase==1;
}
static __attribute__((unused)) void trace_dpu_first_frame_backlight(unsigned crtc,unsigned encoder,int ret) {
    (void)crtc;(void)encoder;(void)ret;
}
static __attribute__((unused)) int dpu_encoder_wait_for_tx_complete(struct drm_encoder *e) {
    (void)e;tx_waits++;
    pthread_mutex_lock(&tx_lock);
    if(block_tx) {
        waiting=true;pthread_cond_broadcast(&tx_cond);
        while(!release_tx)pthread_cond_wait(&tx_cond,&tx_lock);
    }
    if(tx_return==0||tx_return==-EWOULDBLOCK)tx_done=true;
    pthread_mutex_unlock(&tx_lock);
    return tx_return;
}
#include "actual-first-frame-functions.h"
static const struct drm_panel_funcs funcs={fake_enable,fake_disable};
static struct follower_funcs ffuncs={follower_enable,follower_disable};
static struct drm_panel_follower follower={&ffuncs};
static struct device dev={"test-panel"};
static struct panel_bridge pb;
static struct drm_bridge other={false,NULL};
static struct drm_encoder encoder;
static struct drm_device drm;
static struct drm_crtc_state state;
static struct drm_crtc crtc;
static int cases,failures;
static void check(const char *name,bool good) {printf("CASE %s %s\n",name,good?"PASS":"FAIL");cases++;failures+=!good;}
static void reset(void) {
    if(fixture_ready)pthread_mutex_destroy(&ctx.panel.follower_lock);
    memset(&ctx,0,sizeof(ctx));memset(&bl,0,sizeof(bl));
    ctx.dsi=&dsi;bl.data=&ctx;bl.props.brightness=400;bl.props.power=4;
    drm_panel_init(&ctx.panel,&dev,&funcs,16);fixture_ready=true;
    ctx.panel.backlight=&bl;ctx.panel.prepared=true;ctx.panel.delay_backlight_until_first_frame=true;
    ctx.panel.followers.one=&follower;
    writes=positive_writes=physical_brightness=premature=unclocked=followers_on=followers_off=0;
    enable_failure=tx_return=tx_waits=trace_pending=trace_ready=0;
    clocks_on=true;tx_done=false;block_tx=waiting=release_tx=false;
    pb.bridge.panel_bridge=true;pb.bridge.next=NULL;pb.panel=&ctx.panel;
    other.next=&pb.bridge;encoder.bridge=&other;drm.encoder=&encoder;
    state.enable=state.active=true;state.encoder_mask=1;crtc.dev=&drm;crtc.state=&state;
}
#ifndef BASELINE
static void *run_commit(void *arg) {(void)arg;dpu_kms_first_frame_backlight(&crtc);return NULL;}
static void start_wait(pthread_t *t) {
    block_tx=true;pthread_create(t,NULL,run_commit,NULL);
    pthread_mutex_lock(&tx_lock);while(!waiting)pthread_cond_wait(&tx_cond,&tx_lock);pthread_mutex_unlock(&tx_lock);
}
static void finish_wait(pthread_t t) {
    pthread_mutex_lock(&tx_lock);release_tx=true;pthread_cond_broadcast(&tx_cond);pthread_mutex_unlock(&tx_lock);
    pthread_join(t,NULL);
}
#endif
int main(void) {
    reset();drm_panel_enable(&ctx.panel);
    check("positive_brightness_deferred_on_enable",!positive_writes&&!physical_brightness&&!followers_on);
    reset();ctx.panel.enabled=true;bl.props.power=0;bl.props.brightness=77;
    sofef03f_bl_update(&bl);
    check("forced_early_positive_update_blocked",!positive_writes&&!physical_brightness);
#ifndef BASELINE
    reset();ctx.panel.delay_backlight_until_first_frame=ctx.panel.backlight_ready=true;
    pthread_mutex_destroy(&ctx.panel.follower_lock);drm_panel_init(&ctx.panel,&dev,&funcs,16);
    check("new_policy_fields_default_off",!ctx.panel.delay_backlight_until_first_frame&&!ctx.panel.backlight_ready);
    reset();drm_panel_enable(&ctx.panel);pthread_t t;start_wait(&t);
    check("ctl_or_te_is_not_tx_completion",!ctx.panel.backlight_ready&&!positive_writes&&tx_waits==1);
    bl.props.brightness=123;bl.props.power=0;sofef03f_bl_update(&bl);
    check("pending_brightness_change_stays_dark",!positive_writes&&bl.props.brightness==123);
    finish_wait(t);
    check("tx_done_releases_latest_brightness",ctx.panel.backlight_ready&&physical_brightness==123&&positive_writes==1&&followers_on==1&&!premature&&!unclocked);
    dpu_kms_first_frame_backlight(&crtc);drm_panel_first_frame_done(&ctx.panel);
    check("completed_frame_gate_is_one_shot",tx_waits==1&&positive_writes==1&&followers_on==1);
    drm_panel_disable(&ctx.panel);
    check("disable_blanks_and_resets_gate",!ctx.panel.enabled&&!ctx.panel.backlight_ready&&!physical_brightness&&followers_off==1);
    tx_done=false;drm_panel_enable(&ctx.panel);
    check("new_wake_needs_a_new_frame",!ctx.panel.backlight_ready&&positive_writes==1);
    dpu_kms_first_frame_backlight(&crtc);
    check("second_wake_releases_after_tx",ctx.panel.backlight_ready&&positive_writes==2&&!premature);
    reset();drm_panel_enable(&ctx.panel);tx_return=-ETIMEDOUT;dpu_kms_first_frame_backlight(&crtc);
    check("tx_failure_keeps_panel_dark",!ctx.panel.backlight_ready&&!positive_writes&&!followers_on);
    tx_return=0;dpu_kms_first_frame_backlight(&crtc);
    check("later_success_can_release_backlight",ctx.panel.backlight_ready&&positive_writes==1);
    reset();drm_panel_enable(&ctx.panel);tx_return=-EWOULDBLOCK;dpu_kms_first_frame_backlight(&crtc);
    check("already_completed_tx_is_accepted",ctx.panel.backlight_ready&&positive_writes==1&&!premature);
    reset();drm_panel_enable(&ctx.panel);start_wait(&t);drm_panel_disable(&ctx.panel);
    ctx.panel.prepared=false;clocks_on=false;finish_wait(t);
    check("late_completion_after_disable_has_no_mmio",!ctx.panel.backlight_ready&&!positive_writes&&!unclocked&&!followers_on&&!followers_off);
    reset();enable_failure=-EIO;drm_panel_enable(&ctx.panel);dpu_kms_first_frame_backlight(&crtc);
    check("failed_panel_enable_does_not_wait_or_light",!ctx.panel.enabled&&!tx_waits&&!positive_writes);
    reset();drm_panel_enable(&ctx.panel);state.active=false;dpu_kms_first_frame_backlight(&crtc);
    check("inactive_crtc_does_not_wait",!tx_waits&&!positive_writes);
    reset();ctx.panel.delay_backlight_until_first_frame=false;drm_panel_enable(&ctx.panel);dpu_kms_first_frame_backlight(&crtc);
    check("ordinary_panels_keep_immediate_backlight",ctx.panel.backlight_ready&&positive_writes==1&&followers_on==1&&!tx_waits);
    reset();ctx.panel.prepared=false;clocks_on=false;bl.props.power=0;sofef03f_bl_update(&bl);
    check("unprepared_brightness_has_no_mmio",!writes&&!unclocked);
    reset();drm_panel_enable(&ctx.panel);bl.props.power=0;bl.props.brightness=0;sofef03f_bl_update(&bl);
    check("explicit_zero_allowed_while_waiting",writes==1&&!positive_writes&&!physical_brightness&&!unclocked);
    check("non_panel_bridges_are_ignored",!drm_panel_bridge_needs_first_frame(&other));
    drm_panel_bridge_first_frame_done(&other);
#endif
    pthread_mutex_destroy(&ctx.panel.follower_lock);
    printf("CASES %d FAILURES %d\n",cases,failures);return failures?1:0;
}
