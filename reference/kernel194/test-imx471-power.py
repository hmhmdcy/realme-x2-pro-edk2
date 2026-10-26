from pathlib import Path
import hashlib,json,subprocess,os
ref=Path(__file__).resolve().parent;out=Path('/mnt/e/edk2-samurai-out/kernel194');k=Path('/home/cy122/pmos-samurai-kernel136/kernel');source=(k/'drivers/media/i2c/imx471.c').read_text()
def block(marker):
 start=source.index(marker);brace=source.index('{',start);i=brace+1;depth=1
 while depth:depth+=(source[i]=='{')-(source[i]=='}');i+=1
 return source[start:i]
supplies=block('static const char * const imx471_supply_name[]')+';'
body=block('static int imx471_power_off(')+'\n'+block('static int imx471_power_on(')
stub=r'''
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <errno.h>
#define ARRAY_SIZE(a) ((int)(sizeof(a)/sizeof((a)[0])))
struct v4l2_subdev {int unused;};struct device {void *data;};
struct imx471 {struct v4l2_subdev sd;int reset_gpio,img_clk,supplies[3];};
static struct imx471 sensor;
#define to_imx471(sd) ((struct imx471 *)(sd))
static int pins,rails,clock_on,reset,fail_default,fail_reg,fail_clock,fail_sleep,logs,sleep_calls,order;
static void *dev_get_drvdata(struct device *d) {return d->data;}
static int pinctrl_pm_select_default_state(struct device *d) {(void)d;if(fail_default)return -EIO;pins=1;order=1;return 0;}
static int pinctrl_pm_select_sleep_state(struct device *d) {(void)d;sleep_calls++;if(fail_sleep)return -EBUSY;pins=0;return 0;}
static int regulator_bulk_enable(int n,int *data) {(void)data;if(n!=3||order!=1)abort();if(fail_reg)return -ENOSPC;rails=n;order=2;return 0;}
static int regulator_bulk_disable(int n,int *data) {(void)data;if(n!=3)abort();rails=0;return 0;}
static int clk_prepare_enable(int c) {(void)c;if(rails!=3||!pins)abort();if(fail_clock)return -ERANGE;clock_on=1;return 0;}
static void clk_disable_unprepare(int c) {(void)c;clock_on=0;}
static void gpiod_set_value_cansleep(int g,int v) {(void)g;if(!v&&(!clock_on||rails!=3||!pins))abort();reset=v;}
static void usleep_range(int a,int b) {(void)a;(void)b;}
#define dev_err(...) (logs++)
#define dev_err_probe(dev,ret,...) (logs++,(ret))
'''
main=r'''
int main(void) {
 struct device dev={.data=&sensor.sd};int count=0;
 for(int scenario=0;scenario<7;scenario++) {
  pins=rails=clock_on=logs=sleep_calls=order=0;reset=1;
  fail_default=scenario==1;fail_reg=scenario==2||scenario==4;fail_clock=scenario==3||scenario==5;fail_sleep=scenario==4||scenario==5||scenario==6;
  int rc=imx471_power_on(&dev);
  if(scenario==0||scenario==6) {
   if(rc||rails!=3||!clock_on||reset||!pins)return 1;
   rc=imx471_power_off(&dev);
   if(rails||clock_on||!reset||rc!=(fail_sleep?-EBUSY:0))return 2;
  } else {
   int expected=fail_default?-EIO:fail_reg?-ENOSPC:-ERANGE;
   if(rc!=expected||rails||clock_on||!reset)return 3;
   if(sleep_calls!=(fail_default?0:1))return 4;
   if(fail_sleep&&logs<2)return 5;
  }
  if(!fail_sleep&&pins)return 6;
  count++;
 }
 printf("%d real IMX471 power and error-unwind scenarios passed\n",count);return 0;
}
'''
c=out/'imx471-power-host-private.c';c.write_text(stub+supplies+body+main);exe=out/'imx471-power-host-private'
cc=subprocess.run(['gcc','-std=c11','-Wall','-Wextra','-Werror','-g','-O1','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(c),'-o',str(exe)],capture_output=True,text=True);assert cc.returncode==0,cc.stderr
run=subprocess.run([str(exe)],capture_output=True,text=True,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=1:abort_on_error=1',UBSAN_OPTIONS='halt_on_error=1'));(out/'imx471-power-host-private.log').write_text(run.stdout+run.stderr);assert run.returncode==0 and not run.stderr,(run.returncode,run.stderr)
report=dict(stage=194,source_sha256=hashlib.sha256(source.encode()).hexdigest(),actual_production_power_functions_executed=True,scenarios=7,asan_ubsan_passed=True,three_rails_before_clock_and_reset_release=True,pin_restore_attempted_on_bulk_or_clock_enable_failure=True,original_error_preserved_and_secondary_pin_restore_error_logged=True,hardware_access=False)
(ref/'imx471-power-host-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
