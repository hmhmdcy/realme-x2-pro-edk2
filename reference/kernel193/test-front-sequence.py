from pathlib import Path
import hashlib,json,subprocess,os
ref=Path(__file__).resolve().parent;out=Path('/mnt/e/edk2-samurai-out/kernel193');source=(ref/'samurai-front-identify.c').read_text()
def block(marker):
 start=source.index(marker);brace=source.index('{',start);depth=1;i=brace+1
 while depth:depth+=(source[i]=='{')-(source[i]=='}');i+=1
 return source[start:i]
parts=[block(x) for x in ['static void remember_restore_error(','static int hold_clock_domain(','static void release_clock_domain(','static int enable_ldo(','static int identify_once(','static void power_off(']]
stub=r'''
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <errno.h>
#include <string.h>
#include <stdlib.h>
typedef uint8_t u8;
#define ARRAY_SIZE(a) ((int)(sizeof(a)/sizeof((a)[0])))
#define I2C_M_RD 1
struct gpio_desc {int value;};
struct regulator {int refs;};
struct clk {int refs;};
struct regmap {u8 data[65536];};
struct device {int refs;struct device *parent;};
struct i2c_adapter {struct device dev;};
struct i2c_msg {unsigned addr,flags,len;u8 *buf;};
struct front_resources {
 struct regmap *ldos;struct regulator *vio,*s8;struct gpio_desc *reset,*select;
 struct clk *clock;struct i2c_adapter *cci;
 u8 old_vset[2][2],old_enable[7];bool snapshot,s8_on,vio_on,clock_on,reset_output,select_output,cci_active;
};
static unsigned int sensor_id,ready_samples;
static int restore_result,operation,fail_at,partial,wrong_id,off_start,reads;
static int fail(void) {return ++operation==fail_at;}
static struct device *domain;
static int pm_runtime_resume_and_get(struct device *d) {if(fail())return -EIO;d->refs++;return 0;}
static int pm_runtime_put_sync(struct device *d) {d->refs--;return fail()?-EIO:0;}
static void usleep_range(int a,int b) {(void)a;(void)b;}
static int gpiod_direction_output(struct gpio_desc *g,int value) {if(fail())return -EIO;g->value=value;return 0;}
static void gpiod_set_value_cansleep(struct gpio_desc *g,int value) {g->value=value;}
static int regulator_enable(struct regulator *r) {if(fail())return -EIO;r->refs++;return 0;}
static int regulator_disable(struct regulator *r) {if(fail())return -EIO;if(--r->refs<0)abort();return 0;}
static int clk_prepare_enable(struct clk *c) {if(!domain->refs)abort();if(fail())return -EIO;c->refs++;return 0;}
static void clk_disable_unprepare(struct clk *c) {if(--c->refs<0)abort();}
static int regmap_bulk_write(struct regmap *m,unsigned reg,const u8 *bytes,unsigned count) {
 if((reg!=0x4440&&reg!=0x4140)||count!=2)abort();
 if(fail())return -EIO;memcpy(m->data+reg,bytes,count);return 0;
}
static int regmap_write(struct regmap *m,unsigned reg,unsigned value) {
 if((reg!=0x4446&&reg!=0x4146)||(value!=0&&value!=0x80))abort();
 if(fail())return -EIO;m->data[reg]=value;return 0;
}
static int poll(struct regmap *m,unsigned reg,unsigned *value) {
 if((reg!=0x4408&&reg!=0x4108)||m->data[reg+0x3e]!=0x80)abort();
 if(fail())return -ETIMEDOUT;*value=0x80;return 0;
}
#define regmap_read_poll_timeout(map,reg,val,condition,delay,timeout) poll(map,reg,&val)
static int i2c_transfer(struct i2c_adapter *a,struct i2c_msg *m,int n) {
 (void)a;reads++;
 if(n!=2||m[0].addr!=0x10||m[0].len!=2||m[0].buf[0]||m[0].buf[1]!=0x16||m[1].flags!=I2C_M_RD||m[1].len!=2)abort();
 if(fail())return -ENXIO;
 m[1].buf[0]=wrong_id?0x12:0x04;m[1].buf[1]=wrong_id?0x34:0x71;
 return partial?1:2;
}
'''
main=r'''
int main(void) {
 int scenarios=0;
 for(int mode=0;mode<3;mode++)for(int failure=0;failure<=13;failure++) {
  struct regmap map={0};struct regulator vio={0},s8={3};struct gpio_desc reset={1},select={0};struct clk clock={0};struct i2c_adapter cci={0};
  struct front_resources f={.ldos=&map,.vio=&vio,.s8=&s8,.reset=&reset,.select=&select,.clock=&clock,.cci=&cci,.snapshot=true,.old_vset={{0x08,0x07},{0xb0,0x04}}};
  struct device power_domain={0};domain=&power_domain;cci.dev.parent=domain;
  memcpy(map.data+0x4440,f.old_vset[0],2);memcpy(map.data+0x4140,f.old_vset[1],2);
  restore_result=operation=sensor_id=ready_samples=reads=0;fail_at=failure;partial=mode==1;wrong_id=mode==2;
  int ret=hold_clock_domain(&f);if(!ret)ret=identify_once(&f);off_start=operation;power_off(&f);release_clock_domain(&f);
  if(restore_result||vio.refs||s8.refs!=3||clock.refs||select.value||reset.value!=1||map.data[0x4446]||map.data[0x4146]||memcmp(map.data+0x4440,f.old_vset[0],2)||memcmp(map.data+0x4140,f.old_vset[1],2))return 1;
  if(!failure&&((mode==0&&ret)||(mode==1&&ret!=-EIO)||(mode==2&&ret!=-ENODEV)))return 2;
  if(failure&&ret>=0)return 3;
  if(reads>1)return 4;
  if(domain->refs||f.cci_active)return 6;
  scenarios++;
 }
 /* Each fallible shutdown operation reports its error and still visits the rest. */
 for(int failure=1;failure<=7;failure++) {
  struct regmap map={0};struct regulator vio={1},s8={4};struct gpio_desc reset={0},select={1};struct clk clock={1};
  struct front_resources f={.ldos=&map,.vio=&vio,.s8=&s8,.reset=&reset,.select=&select,.clock=&clock,.snapshot=true,.s8_on=true,.vio_on=true,.clock_on=true,.reset_output=true,.select_output=true};
  struct i2c_adapter cci={0};struct device power_domain={.refs=1};domain=&power_domain;cci.dev.parent=domain;f.cci=&cci;f.cci_active=true;
  operation=restore_result=0;fail_at=failure;power_off(&f);release_clock_domain(&f);
  if(restore_result!=-EIO||operation!=7||clock.refs||reset.value!=1||select.value||domain->refs)return 5;
  scenarios++;
 }
 printf("%d actual power sequence/unwind scenarios passed\n",scenarios);return 0;
}
'''
c=out/'front-sequence-host-private.c';c.write_text(stub+'\n'.join(parts)+main);exe=out/'front-sequence-host-private'
cc=subprocess.run(['gcc','-std=c11','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-g','-O1','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(c),'-o',str(exe)],capture_output=True,text=True);assert cc.returncode==0,cc.stderr
run=subprocess.run([str(exe)],capture_output=True,text=True,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=1:abort_on_error=1',UBSAN_OPTIONS='halt_on_error=1'));(out/'front-sequence-host-tests-private.log').write_text(run.stdout+run.stderr);assert run.returncode==0 and not run.stderr,(run.returncode,run.stdout,run.stderr)
report=dict(stage=193,source_sha256=hashlib.sha256(source.encode()).hexdigest(),actual_power_and_unwind_functions_executed=True,scenarios=49,asan_ubsan_passed=True,power_step_failure_unwinds=True,clock_requires_live_power_domain=True,domain_reference_balanced=True,partial_read_and_wrong_id_rejected=True,cleanup_errors_reported_and_remaining_steps_attempted=True,non_camera_register_writes_abort_test=True,hardware_access=False)
(ref/'front-sequence-host-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
