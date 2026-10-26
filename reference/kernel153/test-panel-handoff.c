#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdio.h>
#include <stddef.h>
#include <string.h>
#define GPIOD_ASIS 0
#define GPIOD_OUT_LOW 1
#define GPIOD_OUT_HIGH 2
#define IS_ERR(p) ((long)(p)<0)
#define PTR_ERR(p) ((long)(p))
#define dev_err_probe(dev,err,...) (err)
#define dev_err(...) ((void)0)
struct device {int dummy;};
struct drm_panel {int dummy;};
struct gpio_desc {int id,value,output;};
struct regulator {int refs,id;};
struct regulator_bulk_data {struct regulator *consumer;const char *supply;};
struct mipi_dsi_device {struct device dev;};
struct sofef03f {struct drm_panel panel;struct mipi_dsi_device *dsi;
    struct gpio_desc *reset,*vci,*vddd;struct regulator_bulk_data *supplies;bool supply_enabled[2];};
static struct gpio_desc gpio[3];
static struct regulator regulators[2];
static struct regulator_bulk_data supplies[2];
static struct mipi_dsi_device dsi;
static struct sofef03f ctx;
static int gpio_error,reg_error,on_error,gpio_writes,unsafe_writes;
static bool quiesced;
static struct sofef03f *to_sofef03f(struct drm_panel *p){return (struct sofef03f *)((char *)p - offsetof(struct sofef03f,panel));}
static int gpiod_direction_output(struct gpio_desc *p,int value){
    if(gpio_error==p->id+1)return -EIO;
    gpio_writes++;unsafe_writes+=!quiesced;p->output=1;p->value=value;return 0;
}
static struct gpio_desc *devm_gpiod_get(struct device *dev,const char *name,int flags){
    (void)dev;int i=!strcmp(name,"reset")?0:!strcmp(name,"vci-enable")?1:2;
    struct gpio_desc *p=&gpio[i];
    if(flags!=GPIOD_ASIS)gpiod_direction_output(p,flags==GPIOD_OUT_HIGH);
    return p;
}
static void gpiod_set_value_cansleep(struct gpio_desc *p,int value){assert(p->output);p->value=value;gpio_writes++;unsafe_writes+=!quiesced;}
static int regulator_enable(struct regulator *r){if(reg_error==r->id+1)return -EIO;r->refs++;return 0;}
static int regulator_disable(struct regulator *r){assert(r->refs>0);r->refs--;return 0;}
static void msleep(int n){(void)n;}
static void usleep_range(int a,int b){(void)a;(void)b;}
static int sofef03f_on(struct sofef03f *c){(void)c;return on_error;}
#include "actual-panel-functions.h"
static int failed;
static void check(const char *name,bool ok){printf("CASE %s %s\n",name,ok?"PASS":"FAIL");failed+=!ok;}
static void init(void){
    memset(&ctx,0,sizeof(ctx));ctx.dsi=&dsi;ctx.supplies=supplies;
    for(int i=0;i<3;i++){gpio[i]=(struct gpio_desc){i,i==0?0:1,1};}
    for(int i=0;i<2;i++){regulators[i]=(struct regulator){0,i};supplies[i]=(struct regulator_bulk_data){&regulators[i],"rail"};}
    gpio_error=reg_error=on_error=gpio_writes=unsafe_writes=0;quiesced=false;
}
int main(void){
    init();assert(!actual_probe_gpios(&ctx));
    check("probe_preserves_reset_and_power",gpio[0].value==0&&gpio[1].value==1&&gpio[2].value==1);
    check("probe_does_not_cut_running_frame",!gpio_writes&&!unsafe_writes);
    quiesced=true;check("normal_prepare",!sofef03f_prepare(&ctx.panel)&&ctx.supply_enabled[0]&&ctx.supply_enabled[1]&&gpio[0].value==0&&gpio[1].value==1&&gpio[2].value==1);
    sofef03f_power_off(&ctx);check("normal_teardown",!regulators[0].refs&&!regulators[1].refs&&gpio[0].value==1&&!gpio[1].value&&!gpio[2].value);
    for(int i=1;i<=3;i++){
        init();assert(!actual_probe_gpios(&ctx));quiesced=true;gpio_error=i;
        int ret=sofef03f_prepare(&ctx.panel);char name[80];snprintf(name,sizeof(name),"gpio_direction_failure_%d_has_no_regulator_refs",i);
        check(name,ret==-EIO&&!regulators[0].refs&&!regulators[1].refs);
    }
    for(int i=1;i<=2;i++){
        init();assert(!actual_probe_gpios(&ctx));quiesced=true;reg_error=i;
        int ret=sofef03f_prepare(&ctx.panel);char name[80];snprintf(name,sizeof(name),"regulator_failure_%d_unwinds",i);
        check(name,ret==-EIO&&!regulators[0].refs&&!regulators[1].refs);
    }
    init();assert(!actual_probe_gpios(&ctx));quiesced=true;on_error=-EIO;
    check("dcs_failure_powers_off",sofef03f_prepare(&ctx.panel)==-EIO&&!regulators[0].refs&&!regulators[1].refs&&gpio[0].value==1&&!gpio[1].value&&!gpio[2].value);
    init();for(int i=0;i<3;i++)gpio[i].output=0;
    assert(!actual_probe_gpios(&ctx));quiesced=true;
    int ret=sofef03f_prepare(&ctx.panel);
    check("cold_boot_configures_output_directions",!ret&&gpio[0].output&&gpio[1].output&&gpio[2].output);
    printf("FAILURES %d\n",failed);return failed?1:0;
}
