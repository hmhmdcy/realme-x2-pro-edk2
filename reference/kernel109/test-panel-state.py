"""Compile actual candidate callbacks with fault-injected DCS/regulator APIs."""
from pathlib import Path
import json, subprocess
out=Path('/mnt/e/edk2-samurai-out/kernel109')
s=(out/'panel-after.c').read_text()
def function(text,name):
    a=text.index('static ',text.index(name+'(')-30)
    start=text.index('{',a);depth=0
    for i in range(start,len(text)):
        depth+=(text[i]=='{')-(text[i]=='}')
        if depth==0:return text[a:i+1]
    raise ValueError(name)
header=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
struct drm_panel { bool prepared,enabled; };
struct mipi_dsi_device { int dev; };
struct regulator_bulk_data { int *consumer; const char *supply; };
struct sofef03f { struct drm_panel panel; struct mipi_dsi_device *dsi;
struct regulator_bulk_data *supplies; int *reset,*vci,*vddd; bool supply_enabled[2]; };
struct mipi_dsi_multi_context { struct mipi_dsi_device *dsi; int accum_err; };
static int enable_calls,disable_calls,disable_error,enable_error,on_error,dcs_error,wait_ms,errors;
static struct sofef03f *to_sofef03f(struct drm_panel *p) { return (struct sofef03f *)p; }
static int regulator_enable(int *p) { enable_calls++; if(enable_error)return enable_error;(*p)++;return 0; }
static int regulator_disable(int *p) { disable_calls++;if(disable_error)return disable_error;(*p)--;assert(*p>=0);return 0; }
static void msleep(int n) { wait_ms+=n; }
static void usleep_range(int a,int b) { (void)a;(void)b; }
static void gpiod_set_value_cansleep(int *p,int n) { *p=n; }
static int sofef03f_on(struct sofef03f *c) { (void)c;return on_error; }
static void dcs(struct mipi_dsi_multi_context *c) { c->accum_err=dcs_error; }
#define mipi_dsi_dcs_set_display_off_multi dcs
#define mipi_dsi_dcs_enter_sleep_mode_multi dcs
#define mipi_dsi_msleep(c,n) do { if(!(c)->accum_err)msleep(n); } while(0)
#define dev_err(...) do { errors++; } while(0)
#define dev_warn(...) do { errors++; } while(0)
'''
names=['sofef03f_supply_enable','sofef03f_supply_disable','sofef03f_power_off','sofef03f_prepare','sofef03f_disable','sofef03f_unprepare']
body='\n\n'.join(function(s,n) for n in names)
main=r'''
int main(void) {
  int refs[2]={0}, reset=1,vci=0,vddd=0;
  struct mipi_dsi_device dsi={0};
  struct regulator_bulk_data supplies[2]={{&refs[0],"vddio"},{&refs[1],"vdda"}};
  struct sofef03f ctx={.dsi=&dsi,.supplies=supplies,.reset=&reset,.vci=&vci,.vddd=&vddd};
  assert(!sofef03f_prepare(&ctx.panel));assert(refs[0]==1&&refs[1]==1);
  ctx.panel.prepared=ctx.panel.enabled=true;dcs_error=-110;wait_ms=0;
  if(!sofef03f_disable(&ctx.panel))ctx.panel.enabled=false;
  if(!sofef03f_unprepare(&ctx.panel))ctx.panel.prepared=false;
  assert(!ctx.panel.enabled&&!ctx.panel.prepared&&wait_ms==142);
  assert(reset==1&&vci==0&&vddd==0&&refs[0]==0&&refs[1]==0&&errors==2);
  dcs_error=0;assert(!sofef03f_prepare(&ctx.panel));
  assert(refs[0]==1&&refs[1]==1&&reset==0&&vci==1&&vddd==1);
  disable_error=-5;assert(!sofef03f_unprepare(&ctx.panel));
  assert(refs[0]==1&&refs[1]==1&&reset==1&&vci==0&&vddd==0);
  int old_enables=enable_calls;
  assert(!sofef03f_prepare(&ctx.panel));assert(enable_calls==old_enables);
  disable_error=0;assert(!sofef03f_unprepare(&ctx.panel));
  assert(refs[0]==0&&refs[1]==0);
  on_error=-110;assert(sofef03f_prepare(&ctx.panel)==-110);
  assert(refs[0]==0&&refs[1]==0&&reset==1&&vci==0&&vddd==0);
  on_error=0;enable_error=-5;assert(sofef03f_prepare(&ctx.panel)==-5);
  assert(refs[0]==0&&refs[1]==0);
  printf("PASS: actual callbacks; DCS timeout teardown/reprepare; regulator failure references; prepare rollback\n");
  return 0;
}
'''
p=out/'panel-state-test.c';p.write_text(header+body+main)
subprocess.run(['gcc','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p),'-o',str(out/'panel-state-test')],check=True)
result=subprocess.check_output([str(out/'panel-state-test')],text=True)
(out/'panel-tests.json').write_text(json.dumps(dict(pass_actual_callbacks=True,dcs_timeout_shutdown=True,stock_wait_on_error=True,regulator_failure_balanced=True,prepare_error_rollback=True,hardware_test=False),indent=2)+'\n')
print(result.strip())
