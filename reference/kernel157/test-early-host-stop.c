#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uint32_t u32;
#define DSI_MAX 2
#define DSI_1 1
#define REG_DSI_CTRL 0
#define DSI_CTRL_ENABLE 1u
#define DBG(...) ((void)0)
#define dev_info(dev, ...) ((void)(dev), (void)snprintf(NULL,0,__VA_ARGS__))
#define dev_err(dev, ...) ((void)(dev), (void)snprintf(NULL,0,__VA_ARGS__))
#define pr_err(...) ((void)snprintf(NULL,0,__VA_ARGS__))
struct device { int id; };
struct platform_device { struct device dev; };
struct mutex { int held; };
struct msm_dsi_host {
    bool firmware_quiesced, power_on;
    struct platform_device *pdev;
    struct mutex dev_mutex;
    u32 ctrl;
    int pm_error, readback_error;
};
struct mipi_dsi_host { struct msm_dsi_host *owner; };
struct msm_dsi_phy { int id; };
struct msm_dsi_phy_shared_timings { int unused; };
struct msm_dsi {
    struct mipi_dsi_host *host;
    struct platform_device *pdev;
    struct msm_dsi_phy *phy;
};
struct drm_bridge { int id; };
static struct msm_dsi_host hosts[2];
static struct platform_device pdevs[2];
static struct mipi_dsi_host links[2];
static struct msm_dsi_phy phys[2];
static struct msm_dsi dsis[2];
static bool bonded, peer_present;
static int get_count, put_count, reads, writes, phy_on, phy_off, host_on[2], host_off[2], irqs[2];
static int phy_error, host_error[2], locks;
static char order[128];
static void event(char c) { size_t n=strlen(order);assert(n+1<sizeof(order));order[n]=c;order[n+1]=0; }
static struct msm_dsi_host *to_msm_dsi_host(struct mipi_dsi_host *h) { return h->owner; }
static void mutex_lock(struct mutex *m) { assert(!m->held);m->held=1;locks++; }
static void mutex_unlock(struct mutex *m) { assert(m->held);m->held=0;locks--; }
static int pm_runtime_resume_and_get(struct device *d) { get_count++;return hosts[d->id].pm_error; }
static void pm_runtime_put_sync(struct device *d) { (void)d;put_count++; }
static u32 dsi_read(struct msm_dsi_host *h,int reg) { (void)reg;reads++;return h->ctrl; }
static void dsi_ctrl_disable(struct msm_dsi_host *h) { writes++;event(h->pdev->dev.id?'b':'a');if (!h->readback_error) h->ctrl=0; }
static void wmb(void) { event('W'); }
static int dsi_mgr_bridge_get_id(struct drm_bridge *b) { return b->id; }
static struct msm_dsi *dsi_mgr_get_dsi(int id) { return id && !peer_present ? NULL : &dsis[id]; }
#define IS_BONDED_DSI() bonded
static int dsi_mgr_phy_enable(int id,struct msm_dsi_phy_shared_timings *t) { (void)id;(void)t;phy_on++;event('P');return phy_error; }
static void dsi_mgr_phy_disable(int id) { (void)id;phy_off++;event('D'); }
static int msm_dsi_host_power_on(struct mipi_dsi_host *h,struct msm_dsi_phy_shared_timings *t,bool b,struct msm_dsi_phy *p) {
    (void)t;(void)b;(void)p;int id=h->owner->pdev->dev.id;host_on[id]++;event(id?'J':'H');return host_error[id];
}
static int msm_dsi_host_power_off(struct mipi_dsi_host *h) { host_off[h->owner->pdev->dev.id]++;event('O');return 0; }
static void msm_dsi_host_enable_irq(struct mipi_dsi_host *h) { irqs[h->owner->pdev->dev.id]++;event('I'); }
#include "actual-functions.h"
static void reset(void) {
    memset(hosts,0,sizeof(hosts));memset(host_on,0,sizeof(host_on));memset(host_off,0,sizeof(host_off));memset(irqs,0,sizeof(irqs));
    memset(host_error,0,sizeof(host_error));memset(order,0,sizeof(order));
    get_count=put_count=reads=writes=phy_on=phy_off=phy_error=locks=0;bonded=false;peer_present=true;
    for (int i=0;i<2;i++) { pdevs[i].dev.id=i;hosts[i].pdev=&pdevs[i];hosts[i].ctrl=0x1f5;links[i].owner=&hosts[i];phys[i].id=i;dsis[i]=(struct msm_dsi){&links[i],&pdevs[i],&phys[i]}; }
}
static int cases, failures;
#define CASE(n,expr) do { bool ok=(expr);printf("CASE %s %s\n",n,ok?"PASS":"FAIL");cases++;failures+=!ok; } while(0)
static bool precedes(char a,char b) { const char *x=strchr(order,a),*y=strchr(order,b);return x && y && x<y; }
int main(void) {
    struct drm_bridge bridge={0};int ret;
    reset();ret=dsi_mgr_bridge_power_on(&bridge);
    CASE("single_stops_before_phy",ret==0 && precedes('a','P') && precedes('P','H') && irqs[0]==1 && locks==0);
    reset();bonded=true;ret=dsi_mgr_bridge_power_on(&bridge);
    CASE("both_hosts_stop_before_phy",ret==0 && precedes('a','P') && precedes('b','P') && host_on[1]==1 && irqs[1]==1 && locks==0);
#ifndef BASELINE
    reset();ret=msm_dsi_host_quiesce_firmware(&links[0]);
    CASE("stop_readback_and_balanced_runtime",ret==0 && hosts[0].firmware_quiesced && hosts[0].ctrl==0 && get_count==1 && put_count==1 && reads==2 && writes==1 && locks==0);
    ret=msm_dsi_host_quiesce_firmware(&links[0]);
    CASE("second_handoff_no_mmio_or_vote",ret==0 && get_count==1 && put_count==1 && reads==2 && writes==1 && locks==0);
    reset();hosts[0].power_on=true;ret=msm_dsi_host_quiesce_firmware(&links[0]);
    CASE("native_live_host_untouched",ret==0 && hosts[0].ctrl==0x1f5 && !reads && !writes && !get_count && !put_count && locks==0);
    reset();hosts[0].pm_error=-ENOMEM;ret=msm_dsi_host_quiesce_firmware(&links[0]);
    CASE("runtime_error_no_unclocked_mmio",ret==-ENOMEM && !hosts[0].firmware_quiesced && !reads && !writes && get_count==1 && !put_count && locks==0);
    reset();hosts[0].readback_error=1;ret=msm_dsi_host_quiesce_firmware(&links[0]);
    CASE("failed_stop_not_marked_success",ret==-EIO && !hosts[0].firmware_quiesced && get_count==put_count && locks==0);
    hosts[0].readback_error=0;ret=msm_dsi_host_quiesce_firmware(&links[0]);
    CASE("failed_stop_can_retry",ret==0 && hosts[0].firmware_quiesced && hosts[0].ctrl==0 && get_count==2 && put_count==2 && locks==0);
    reset();hosts[0].ctrl=0;ret=msm_dsi_host_quiesce_firmware(&links[0]);
    CASE("already_stopped_controller_valid",ret==0 && hosts[0].firmware_quiesced && reads==2 && get_count==put_count && locks==0);
    reset();hosts[0].pm_error=-ENOMEM;ret=dsi_mgr_bridge_power_on(&bridge);
    CASE("manager_aborts_before_phy_on_vote_failure",ret==-ENOMEM && !phy_on && !host_on[0] && !irqs[0] && locks==0);
    reset();bonded=true;hosts[1].pm_error=-ENOMEM;ret=dsi_mgr_bridge_power_on(&bridge);
    CASE("peer_failure_blocks_shared_phy",ret==-ENOMEM && hosts[0].firmware_quiesced && !hosts[1].firmware_quiesced && !phy_on && !irqs[0] && locks==0);
    hosts[1].pm_error=0;ret=dsi_mgr_bridge_power_on(&bridge);
    CASE("peer_retry_preserves_first_stop",ret==0 && writes==2 && phy_on==1 && irqs[0]==1 && irqs[1]==1 && get_count==3 && put_count==2 && locks==0);
    reset();phy_error=-ETIMEDOUT;ret=dsi_mgr_bridge_power_on(&bridge);
    CASE("phy_failure_does_not_enable_host",ret==-ETIMEDOUT && hosts[0].firmware_quiesced && !host_on[0] && !irqs[0] && get_count==put_count && locks==0);
    reset();host_error[0]=-EIO;ret=dsi_mgr_bridge_power_on(&bridge);
    CASE("first_host_failure_unwinds_phy",ret==-EIO && phy_off==1 && !host_off[0] && !irqs[0] && locks==0);
    reset();bonded=true;host_error[1]=-EIO;ret=dsi_mgr_bridge_power_on(&bridge);
    CASE("peer_host_failure_unwinds_first_host_phy",ret==-EIO && host_off[0]==1 && phy_off==1 && !irqs[0] && !irqs[1] && locks==0);
#endif
    printf("RESULT cases=%d failures=%d\n",cases,failures);return failures?1:0;
}
