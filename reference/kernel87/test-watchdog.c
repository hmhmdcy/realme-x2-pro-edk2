/* Deterministic API-level interleavings of the actual extracted driver functions.
 * Timer/IRQ infrastructure is stubbed; hardware and real SMP scheduling are not.
 */
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef uint32_t u32;
typedef struct { int v; } atomic_t;
struct timer_list { unsigned long expires; int pending; };
struct drm_mode { int refresh; };
struct drm_crtc_state { struct drm_mode adjusted_mode; };
struct drm_crtc { struct drm_crtc_state *state; };
struct drm_encoder { void *dev; struct drm_crtc *crtc; int id; };
struct hw { int idx; };
struct dpu_encoder_phys { int intf_mode; struct hw *hw_intf, *hw_wb; };
struct dpu_encoder_virt {
    struct drm_encoder base;
    unsigned long frame_busy_mask[1];
    atomic_t frame_done_timeout_ms, frame_done_timeout_cnt;
    unsigned long frame_done_deadline;
    struct timer_list frame_done_timer;
    struct drm_crtc *crtc;
    int enc_spinlock, num_phys_encs;
    struct dpu_encoder_phys *phys_encs[2];
};
enum { DPU_ENCODER_FRAME_EVENT_DONE=1, DPU_ENCODER_FRAME_EVENT_ERROR=2,
       DPU_ENCODER_FRAME_EVENT_PANEL_DEAD=4, DPU_ENC_RC_EVENT_FRAME_DONE=2 };
#define DPU_ENCODER_FRAME_DONE_TIMEOUT_FRAMES 10
#define DRMID(e) ((e)->id)
#define to_dpu_encoder_virt(e) ((struct dpu_encoder_virt *)(e))
#define timer_container_of(name,t,member) ((struct dpu_encoder_virt *)((char *)(t)-offsetof(struct dpu_encoder_virt,member)))
#define time_before(a,b) ((long)((a)-(b))<0)
static unsigned long jiffies;
static int held, done_notifications, error_notifications, timeout_events, snapshots, stale;
static void check(int value, const char *message) { if(!value) {fprintf(stderr,"FAIL %s\n",message);exit(1);} }
#define spin_lock_irqsave(lock,flags) do { (void)(lock); (flags)=0; check(!held,"lock recursion");held=1; } while(0)
#define spin_unlock_irqrestore(lock,flags) do { (void)(lock);(void)(flags);check(held,"unlock without lock");held=0; } while(0)
static int atomic_read(atomic_t *a) {return a->v;}
static void atomic_set(atomic_t *a,int v) {a->v=v;}
static int atomic_xchg(atomic_t *a,int v) {int r=a->v;a->v=v;return r;}
static int atomic_inc_return(atomic_t *a) {return ++a->v;}
static unsigned long msecs_to_jiffies(unsigned long ms) {return (ms+3)/4;}
static int drm_mode_vrefresh(struct drm_mode *m) {return m->refresh;}
static void mod_timer(struct timer_list *t,unsigned long expires) {t->expires=expires;t->pending=1;}
static void timer_delete(struct timer_list *t) {t->pending=0;}
static void clear_bit(unsigned int b,unsigned long *mask) {*mask&=~(1UL<<b);}
#define trace_dpu_enc_frame_done_cb_not_busy(...) do {} while(0)
#define trace_dpu_enc_frame_done_cb(...) do {} while(0)
#define dpu_encoder_helper_get_intf_type(...) "cmd"
#define DRM_DEBUG_KMS(...) do {} while(0)
#define DPU_ERROR(...) do {check(!held,"printk while lock held");} while(0)
#define DPU_ERROR_ENC_RATELIMITED(...) do {check(!held,"printk while lock held");} while(0)
static void trace_dpu_enc_frame_watchdog(uint32_t id,const char *action,unsigned long busy,unsigned long now,unsigned long deadline,int ms)
{ (void)id;(void)busy;(void)now;(void)deadline;(void)ms;check(held,"state trace outside lock");if(!strcmp(action,"expire_stale"))stale++; }
static void trace_dpu_enc_frame_done_timeout(uint32_t id,u32 event)
{(void)id;(void)event;check(!held,"timeout event while lock held");timeout_events++;}
static void msm_disp_snapshot_state(void *dev)
{(void)dev;check(!held,"snapshot while lock held");snapshots++;}
static int dpu_encoder_resource_control(struct drm_encoder *e,u32 event)
{(void)e;(void)event;check(!held,"resource callback while lock held");return 0;}
static void dpu_crtc_frame_event_cb(struct drm_crtc *crtc,u32 event)
{(void)crtc;check(!held,"CRTC callback while lock held");if(event&1)done_notifications++;if(event&2)error_notifications++;}

#include "watchdog-functions.inc"

static struct dpu_encoder_virt enc;
static struct dpu_encoder_phys phys[2];
static struct drm_crtc_state state;
static struct drm_crtc crtc;
static void setup(void)
{
    memset(&enc,0,sizeof(enc));memset(phys,0,sizeof(phys));
    state.adjusted_mode.refresh=60;crtc.state=&state;enc.crtc=&crtc;
    enc.base.crtc=&crtc;enc.base.dev=&enc;enc.base.id=35;
    enc.num_phys_encs=2;enc.phys_encs[0]=&phys[0];enc.phys_encs[1]=&phys[1];
    held=done_notifications=error_notifications=timeout_events=snapshots=stale=0;jiffies=100;
}
static void arm(void) {dpu_encoder_start_frame_done_timer(&enc.base);check(!held,"arm leaked lock");}
static void finish(unsigned int p) {dpu_encoder_frame_done_callback(&enc.base,&phys[p],1);check(!held,"completion leaked lock");}
static void expire(void) {dpu_encoder_frame_done_timeout(&enc.frame_done_timer);check(!held,"expiry leaked lock");}
int main(void)
{
    setup();arm();check(!enc.frame_done_timer.pending && !atomic_read(&enc.frame_done_timeout_ms),"post-completion arm must remain inactive");
    puts("PASS completion preceding post-kickoff timer arm");
    setup();enc.frame_busy_mask[0]=1;arm();finish(0);jiffies=200;expire();
    check(!timeout_events && !error_notifications && done_notifications==1 && !enc.frame_done_timer.pending,"completed frame cannot expire");
    puts("PASS completed frame and already dispatched old callback");
    setup();enc.frame_busy_mask[0]=1;arm();jiffies=150;arm();unsigned long deadline=enc.frame_done_deadline;
    jiffies=151;expire();check(!timeout_events && !error_notifications && stale==1 && atomic_read(&enc.frame_done_timeout_ms)>0 && enc.frame_done_deadline==deadline && enc.frame_done_timer.pending,"old callback must preserve new deadline");
    jiffies=deadline;enc.frame_done_timer.pending=0;expire();expire();
    check(timeout_events==1 && error_notifications==1 && snapshots==1 && atomic_read(&enc.frame_done_timeout_cnt)==1,"genuine stall reports exactly once");
    finish(0);check(done_notifications==1 && !enc.frame_busy_mask[0],"completion after a real expiry still delivered");
    puts("PASS rearm overlap, genuine stall and late completion");
    setup();enc.frame_busy_mask[0]=3;arm();finish(0);
    check(enc.frame_busy_mask[0]==2 && enc.frame_done_timer.pending && !done_notifications,"other physical encoder remains pending");
    finish(1);check(!enc.frame_busy_mask[0] && !enc.frame_done_timer.pending && done_notifications==1,"last encoder completion disarms");
    puts("PASS multi-encoder completion");
    setup();enc.frame_busy_mask[0]=1;jiffies=ULONG_MAX-10;arm();deadline=enc.frame_done_deadline;
    jiffies=ULONG_MAX-1;expire();check(!timeout_events && atomic_read(&enc.frame_done_timeout_ms)>0,"wrapped deadline not prematurely expired");
    jiffies=deadline;enc.frame_done_timer.pending=0;expire();check(timeout_events==1,"wrapped deadline still expires");
    puts("PASS unsigned jiffies wraparound");
    setup();enc.frame_busy_mask[0]=1;arm();enc.crtc=NULL;jiffies=enc.frame_done_deadline;expire();check(!timeout_events,"detached CRTC receives no timeout");
    puts("PASS absent CRTC");
    return 0;
}
