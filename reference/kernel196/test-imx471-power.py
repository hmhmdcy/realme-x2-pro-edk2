from pathlib import Path
import hashlib,json,os,resource,subprocess
k=Path('/home/cy122/pmos-samurai-kernel136/kernel');ref=Path(__file__).resolve().parent;out=Path('/mnt/e/edk2-samurai-out/kernel196');source=(k/'drivers/media/i2c/imx471.c').read_text();defs=source[source.index('enum imx471_supply'):source.index('struct imx471_mode')];block=source[source.index('/* Keep the interface and analogue rails'):source.index('static int imx471_enable_stream(')]
stub=r'''
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#define ARRAY_SIZE(x) ((int)(sizeof(x)/sizeof((x)[0])))
struct device { int has_of; };struct regulator { int id; };struct regulator_bulk_data { struct regulator *consumer; };
struct v4l2_subdev { int unused; };struct clk { int unused; };struct gpio_desc { int unused; };
struct imx471 { struct v4l2_subdev sd;struct device *dev;struct regulator_bulk_data supplies[3];struct clk *img_clk;struct gpio_desc *reset_gpio; };
static struct imx471 sensor;static struct device device;static struct regulator supplies[3];static struct clk clock_obj;static struct gpio_desc reset_obj;
static int enabled,clock_on,reset_asserted,events[48],count,fail_rail,fail_clock,fail_active,fail_sleep,bulk_fail,logs,cases;
#define dev_get_drvdata(d) ((void)(d), &sensor.sd)
#define to_imx471(p) ((struct imx471 *)((char *)(p)-offsetof(struct imx471,sd)))
static void *dev_of_node(struct device *d) { return d->has_of?d:NULL; }
static void event(int v) { assert(count<48);events[count++]=v; }
static int regulator_enable(struct regulator *r) { event(10+r->id);if(device.has_of) {if(r->id==0)assert(enabled&4);if(r->id==1)assert((enabled&5)==5); }if(fail_rail==r->id)return -30-r->id;enabled|=1<<r->id;return 0; }
static int regulator_disable(struct regulator *r) { event(20+r->id);assert(enabled&(1<<r->id));enabled&=~(1<<r->id);return 0; }
static int regulator_bulk_enable(int n,struct regulator_bulk_data *s) { assert(n==3 && s==sensor.supplies);if(bulk_fail)return -40;
 if(device.has_of) { /* A permitted asynchronous bulk scheduling order. */for(int i=1;i>=0;i--){int ret=regulator_enable(s[i].consumer);if(ret)return ret;}return regulator_enable(s[2].consumer); }
 event(50);enabled=7;return 0; }
static int regulator_bulk_disable(int n,struct regulator_bulk_data *s) { assert(n==3 && s==sensor.supplies);event(51);enabled=0;return 0; }
static int pinctrl_pm_select_default_state(struct device *d) { assert(d==&device);event(100);return fail_active?-62:0; }
static int pinctrl_pm_select_sleep_state(struct device *d) { assert(d==&device);event(101);return fail_sleep?-63:0; }
static int clk_prepare_enable(struct clk *c) { assert(c==&clock_obj && enabled==7);event(200);if(fail_clock)return -71;clock_on=1;return 0; }
static void clk_disable_unprepare(struct clk *c) { assert(c==&clock_obj && clock_on);event(201);clock_on=0; }
static void gpiod_set_value_cansleep(struct gpio_desc *g,int v) { assert(g==&reset_obj);event(300+v);reset_asserted=v; }
static void usleep_range(int a,int b) { assert((a==1000&&b==2000)||(a==10000&&b==15000));event(a==1000?400:410); }
static int dev_err_probe(struct device *d,int e,const char *fmt) { assert(d==&device && fmt);logs++;return e; }
#define dev_err(d,...) do { (void)(d);logs++; } while(0)
'''
tests=r'''
static void start(int of) { cases++;device.has_of=of;enabled=clock_on=count=logs=fail_clock=fail_active=fail_sleep=bulk_fail=0;fail_rail=-1;reset_asserted=1;memset(events,0,sizeof(events));sensor.dev=&device;sensor.img_clk=&clock_obj;sensor.reset_gpio=&reset_obj;for(int i=0;i<3;i++){supplies[i].id=i;sensor.supplies[i].consumer=&supplies[i];} }
static void no_power(int expected) { assert(imx471_power_on(&device)==expected);assert(!enabled && !clock_on && reset_asserted); }
int main(void) {
 (void)imx471_supply_name;
 start(1);assert(!imx471_power_on(&device));int on[]={100,12,400,10,400,11,400,200,300,410};assert(count==ARRAY_SIZE(on)&&!memcmp(events,on,sizeof(on))&&enabled==7&&clock_on&&!reset_asserted);
 assert(!imx471_power_off(&device));int off[]={201,301,21,20,22,101};assert(count==ARRAY_SIZE(on)+ARRAY_SIZE(off)&&!memcmp(events+ARRAY_SIZE(on),off,sizeof(off))&&!enabled&&!clock_on&&reset_asserted);
 for(int i=0;i<3;i++){start(1);fail_rail=i;no_power(-30-i);assert(events[count-1]==101);}
 start(1);fail_clock=1;no_power(-71);assert(events[count-1]==101);
 start(1);fail_active=1;no_power(-62);assert(count==1);
 for(int i=0;i<3;i++){start(1);fail_rail=i;fail_sleep=1;no_power(-30-i);assert(logs==2);}
 start(1);fail_clock=1;fail_sleep=1;no_power(-71);assert(logs==2);
 start(1);assert(!imx471_power_on(&device));fail_sleep=1;assert(imx471_power_off(&device)==-63&&!enabled&&!clock_on&&reset_asserted);
 start(0);assert(!imx471_power_on(&device));assert(events[1]==50);assert(!imx471_power_off(&device));assert(events[count-2]==51);
 start(0);bulk_fail=1;no_power(-40);
 start(0);fail_clock=1;no_power(-71);
 start(0);fail_active=1;no_power(-62);
 printf("%d cases passed\n",cases);return 0;
}
'''
p=out/'imx471-power-host-private.c';p.write_text(stub+defs+block+tests);binary=out/'imx471-power-host-private';args=['gcc','-std=gnu11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer','-g']
subprocess.run(args+[str(p),'-o',str(binary)],check=True);run=subprocess.run([str(binary)],capture_output=True,text=True,check=True,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=1'));assert run.stdout.strip()=='15 cases passed',run.stdout
old=(out/'imx471-before196-private.c').read_text();oldblock=old[old.index('static int imx471_power_off('):old.index('static int imx471_enable_stream(')];p=out/'imx471-before196-host-private.c';p.write_text(stub+defs+oldblock+tests);oldbinary=out/'imx471-before196-host-private';subprocess.run(args+['-Wno-unused-function',str(p),'-o',str(oldbinary)],check=True)
def no_core():resource.setrlimit(resource.RLIMIT_CORE,(0,0))
failed=subprocess.run([str(oldbinary)],capture_output=True,preexec_fn=no_core);(out/'before196-regression-failure-private.log').write_bytes(failed.stdout+failed.stderr);assert failed.returncode==-6 and b'Assertion' in failed.stderr
r=dict(stage=196,source_sha256=hashlib.sha256(source.encode()).hexdigest(),actual_power_and_supply_functions_tested=True,cases=15,asan_ubsan_passed=True,old_actual_functions_fail_with_permitted_bulk_schedule=True,of_enable_order_and_delays_verified=True,of_reverse_disable_order_verified=True,acpi_bulk_behavior_preserved=True,no_hardware_access=True);(ref/'imx471-power-host-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
