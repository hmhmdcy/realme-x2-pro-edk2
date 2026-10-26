"""Exercise the actual PM8008 helpers against scripted I2C/GPIO faults."""
from pathlib import Path
import hashlib,json,os,subprocess
ref=Path(__file__).resolve().parent;k=Path('/home/cy122/pmos-samurai-kernel136/kernel');out=Path('/mnt/e/edk2-samurai-out/kernel195')
source=(k/'drivers/mfd/qcom-pm8008.c').read_text();block=source[source.index('#define PM8008_FACTORY_ADDRESS'):source.index('static int pm8008_probe(')]
assert block.strip()==(ref/'pm8008-initial-address.c').read_text().split('/* Add this block before pm8008_probe() in drivers/mfd/qcom-pm8008.c. */')[1].strip()
stub=r'''
#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
typedef uint8_t u8; typedef uint16_t u16; typedef uint32_t u32;
#define ARRAY_SIZE(x) ((int)(sizeof(x)/sizeof((x)[0])))
#define I2C_M_RD 1
#define I2C_CLIENT_TEN 16
#define I2C_FUNC_I2C 1
#define GPIOD_ASIS 0
#define DEFINE_MUTEX(x) int x
#define IS_ERR(x) ((intptr_t)(x)<0)
#define PTR_ERR(x) ((int)(intptr_t)(x))
struct device { int unused; }; struct i2c_adapter { int unused; };
struct gpio_desc { int unused; };
struct i2c_client { struct device dev; struct i2c_adapter *adapter; u16 addr,flags; };
struct i2c_msg { u16 addr,flags,len; u8 *buf; };
struct event { int address,result,write,bad_id; };
static struct event events[8];static int used,total,property,property_error,initial,functionality;
static int gpio_values[4],gpio_count,gpio_fail_call,gpio_error,sleep_count,logs,mutex_depth,mutex_calls,get_error,get_absent,cases,reset_state;
static struct gpio_desc reset_gpio;
static int device_property_present(struct device *d,const char *n) { (void)d; assert(!strcmp(n,"qcom,initial-address"));return property; }
static int device_property_read_u32(struct device *d,const char *n,u32 *v) { (void)d;(void)n;*v=initial;return property_error; }
static int i2c_check_functionality(struct i2c_adapter *a,int f) { assert(a && f==I2C_FUNC_I2C);return functionality; }
static int i2c_transfer(struct i2c_adapter *a,struct i2c_msg *m,int n) {
 assert(a && used<total);struct event e=events[used++];assert(m[0].addr==e.address);
 if(e.write) { assert(n==1 && m[0].len==3 && !m[0].flags);assert(m[0].buf[0]==6 && m[0].buf[1]==0x44 && m[0].buf[2]==1); }
 else { assert(n==2 && m[0].len==2 && !m[0].flags && m[0].buf[0]==1 && m[0].buf[1]==0);assert(m[1].addr==e.address && m[1].flags==I2C_M_RD && m[1].len==6);
  if(e.result==2) { memset(m[1].buf,0,6);m[1].buf[4]=e.bad_id?0:0x51;m[1].buf[5]=0x2c; } }
 return e.result;
}
static int gpiod_direction_output(struct gpio_desc *g,int v) { assert(g==&reset_gpio && gpio_count<4);gpio_values[gpio_count++]=v;if(gpio_count==gpio_fail_call)return gpio_error;reset_state=v;return 0; }
static void usleep_range(int a,int b) { assert((a==1000 && b==2000)||(a==10000 && b==11000));sleep_count++; }
#define dev_err(d,...) do { (void)(d);logs++; } while(0)
#define dev_info(d,...) do { (void)(d);logs++; } while(0)
static struct gpio_desc *devm_gpiod_get_optional(struct device *d,const char *n,int f) { (void)d;assert(!strcmp(n,"reset") && f==GPIOD_ASIS);return get_error?(struct gpio_desc *)(intptr_t)get_error:get_absent?NULL:&reset_gpio; }
static void mutex_lock(int *m) { (void)m;assert(!mutex_depth);mutex_depth++;mutex_calls++; }
static void mutex_unlock(int *m) { (void)m;assert(mutex_depth==1);mutex_depth--; }
'''
tests=r'''
static struct i2c_adapter adapter;
static struct i2c_client client;
static void start(void) {
 memset(events,0,sizeof(events));used=total=0;property=1;property_error=0;initial=8;functionality=1;
 memset(gpio_values,0,sizeof(gpio_values));gpio_count=gpio_fail_call=sleep_count=logs=mutex_depth=mutex_calls=get_error=get_absent=0;gpio_error=-EIO;reset_state=0;
 client=(struct i2c_client){.adapter=&adapter,.addr=4};cases++;
}
static void rd(int a,int r,int bad) { events[total++]=(struct event){a,r,0,bad}; }
static void wr(int r) { events[total++]=(struct event){8,r,1,0}; }
static void finish(int expected,struct gpio_desc *g,int ngpio,int nsleep) {
 assert(pm8008_initialize_address(&client,g)==expected);assert(used==total && gpio_count==ngpio && sleep_count==nsleep);if(expected && ngpio==3 && gpio_fail_call!=3)assert(reset_state==1 && gpio_values[2]==1);
}
static void cold_prefix(int nack) { rd(4,nack,0);rd(8,nack,0); }
int main(void) {
 start();rd(4,2,0);finish(0,&reset_gpio,1,0);assert(gpio_values[0]==0);
 for(int nack=-ENXIO; ;nack=-EREMOTEIO) { start();cold_prefix(nack);rd(8,2,0);wr(1);rd(4,2,0);finish(0,&reset_gpio,2,3);assert(gpio_values[0]==1 && gpio_values[1]==0);if(nack==-EREMOTEIO)break; }
 for(int ack=-EIO;ack<=0;ack+=EIO) { start();cold_prefix(-ENXIO);rd(8,2,0);wr(ack);rd(4,2,0);finish(0,&reset_gpio,2,3); }
 start();rd(4,2,1);finish(-ENODEV,&reset_gpio,0,0);
 start();rd(4,-ETIMEDOUT,0);finish(-ETIMEDOUT,&reset_gpio,0,0);
 start();rd(4,1,0);finish(-EIO,&reset_gpio,0,0);
 for(int bad=0;bad<2;bad++) { start();rd(4,-ENXIO,0);rd(8,2,bad);finish(-EBUSY,&reset_gpio,1,1);assert(gpio_values[0]==1 && logs==1); }
 start();rd(4,-ENXIO,0);rd(8,-ETIMEDOUT,0);finish(-ETIMEDOUT,&reset_gpio,1,1);
 start();rd(4,-ENXIO,0);rd(8,1,0);finish(-EIO,&reset_gpio,1,1);
 start();cold_prefix(-ENXIO);rd(8,2,1);finish(-ENODEV,&reset_gpio,3,2);
 start();cold_prefix(-ENXIO);rd(8,-ENXIO,0);finish(-ENXIO,&reset_gpio,3,2);
 start();cold_prefix(-ENXIO);rd(8,0,0);finish(-EIO,&reset_gpio,3,2);
 start();cold_prefix(-ENXIO);rd(8,2,0);wr(-ETIMEDOUT);rd(4,-ENXIO,0);finish(-ETIMEDOUT,&reset_gpio,3,3);
 start();cold_prefix(-ENXIO);rd(8,2,0);wr(0);rd(4,-ENXIO,0);finish(-EIO,&reset_gpio,3,3);
 start();cold_prefix(-ENXIO);rd(8,2,0);wr(1);rd(4,2,1);finish(-ENODEV,&reset_gpio,3,3);
 start();gpio_fail_call=1;rd(4,-ENXIO,0);finish(-EIO,&reset_gpio,1,0);
 start();gpio_fail_call=2;cold_prefix(-ENXIO);finish(-EIO,&reset_gpio,3,1);
 start();gpio_fail_call=1;rd(4,2,0);finish(-EIO,&reset_gpio,1,0);
 start();property=0;finish(0,NULL,0,1);
 start();property=0;finish(0,&reset_gpio,1,1);assert(gpio_values[0]==0);
 start();property=0;gpio_fail_call=1;finish(-EIO,&reset_gpio,1,0);
 start();property_error=-EOVERFLOW;finish(-EOVERFLOW,&reset_gpio,0,0);
 start();initial=9;finish(-EINVAL,&reset_gpio,0,0);
 start();client.addr=8;finish(-EINVAL,&reset_gpio,0,0);
 start();finish(-EINVAL,NULL,0,0);
 start();client.flags=I2C_CLIENT_TEN;finish(-EINVAL,&reset_gpio,0,0);
 start();functionality=0;finish(-EINVAL,&reset_gpio,0,0);
 start();get_error=-517;assert(pm8008_reset_and_address(&client)==-517);assert(!mutex_calls && !used && !gpio_count);
 start();get_absent=1;property=0;assert(!pm8008_reset_and_address(&client));assert(mutex_calls==1 && !mutex_depth && sleep_count==1);
 start();get_absent=1;assert(pm8008_reset_and_address(&client)==-EINVAL);assert(mutex_calls==1 && !mutex_depth && !gpio_count);
 start();rd(4,2,0);assert(!pm8008_reset_and_address(&client));assert(used==total && mutex_calls==1 && !mutex_depth && gpio_count==1);
 start();rd(4,-ETIMEDOUT,0);assert(pm8008_reset_and_address(&client)==-ETIMEDOUT);assert(used==total && mutex_calls==1 && !mutex_depth);
 start();gpio_fail_call=3;cold_prefix(-ENXIO);rd(8,2,1);finish(-ENODEV,&reset_gpio,3,2);assert(logs==1 && reset_state==0);
 start();gpio_fail_call=3;cold_prefix(-ENXIO);rd(8,2,0);wr(-ETIMEDOUT);rd(4,-ENXIO,0);finish(-ETIMEDOUT,&reset_gpio,3,3);assert(logs==1 && reset_state==0);
 printf("%d cases passed\n",cases);return 0;
}
'''
p=out/'pm8008-address-host-private.c';p.write_text(stub+block+tests);binary=out/'pm8008-address-host-private'
subprocess.run(['gcc','-std=gnu11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer','-g',str(p),'-o',str(binary)],check=True)
run=subprocess.run([str(binary)],text=True,capture_output=True,check=True,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=1'));assert run.stdout.strip()=='37 cases passed',run.stdout
report=dict(stage=195,source_sha256=hashlib.sha256(source.encode()).hexdigest(),tested_actual_helpers=True,cases=37,asan_ubsan_passed=True,includes_cold_warm_occupied_sibling_and_transfer_gpio_property_failures=True,no_hardware_access=True)
# The unchanged stage194 helpers must fail the strengthened reset-state test.
legacy=(ref.parent/'kernel194/pm8008-initial-address.c').read_text().split('/* Add this block before pm8008_probe() in drivers/mfd/qcom-pm8008.c. */')[1]
old_c=out/'pm8008-address-before195-host-private.c';old_binary=out/'pm8008-address-before195-host-private';old_c.write_text(stub+legacy+tests)
subprocess.run(['gcc','-std=gnu11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer','-g',str(old_c),'-o',str(old_binary)],check=True)
import resource
def no_core():resource.setrlimit(resource.RLIMIT_CORE,(0,0))
failed=subprocess.run([str(old_binary)],capture_output=True,preexec_fn=no_core);(out/'before195-regression-failure-private.log').write_bytes(failed.stdout+failed.stderr)
assert failed.returncode==-6 and b'Assertion' in failed.stderr
report.update(previous_actual_helpers_fail_new_regression=True,primary_error_and_cleanup_error_tested=True,reset_state_checked_on_all_cold_release_failures=True)
(ref/'pmic-address-host-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
