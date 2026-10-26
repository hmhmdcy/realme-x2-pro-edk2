"""Execute the actual BU64253 C loader/probe and bounded init callbacks with stubs."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import time

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('init_storage449', HERE.parent / 'kernel449/storage.py')
storage = importlib.util.module_from_spec(spec); spec.loader.exec_module(storage)
storage.mount.mounted_build()
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel453')
text = (HERE / 'bu64253.c').read_text()


def block(prefix):
    start = text.index(prefix)
    brace = text.index('{', start)
    depth = 1; end = brace + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


functions = [
    'static inline struct bu64253 *to_bu64253', 'static int bu64253_write(',
    'static int bu64253_set_position(', 'static int bu64253_load_init(',
    'static int bu64253_power_off(', 'static int bu64253_runtime_resume(',
    'static int bu64253_probe(',
]
parts = [block(p) for p in functions]
definitions = '\n'.join(re.findall(r'^#define BU64253[^\n]+', text, re.M))
preamble = r'''
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef uint8_t u8;
typedef uint16_t u16;
struct device { void *driver; };
struct i2c_client { struct device dev; };
struct firmware { size_t size; const u8 *data; };
struct regulator { unsigned int refs; };
struct mutex { bool held; };
struct entity { int function; };
struct v4l2_subdev { struct device *dev; void *client; const void *internal_ops; int flags; struct entity entity; void *ctrl_handler; };
struct v4l2_ctrl_handler { int error; struct mutex *lock; };
struct v4l2_ctrl { unsigned int flags; };
static int bu64253_ops, bu64253_internal_ops, bu64253_ctrl_ops;
#define container_of(ptr, type, member) ((type *)((char *)(ptr) - offsetof(type, member)))
#define I2C_FUNC_I2C 1
#define GFP_KERNEL 0
#define V4L2_SUBDEV_FL_HAS_DEVNODE 1
#define MEDIA_ENT_F_LENS 2
#define V4L2_CID_FOCUS_ABSOLUTE 3
#define V4L2_CTRL_FLAG_EXECUTE_ON_WRITE 4
#define IS_ERR(p) ((uintptr_t)(p) >= (uintptr_t)-4095)
#define PTR_ERR(p) ((int)(intptr_t)(p))
#define dev_err(...) ((void)0)
static struct firmware input;
static struct regulator supply;
static struct i2c_client client;
static struct v4l2_ctrl focus;
static void *allocated;
static int property_result, request_result, request_calls, release_calls;
static int i2c_calls, enable_calls, disable_calls, regulator_lookups;
static int pm_enable_calls, registrations, fail_write_at, fail_write_result;
static u8 writes[32][2];
static unsigned int sleeps[32], sleep_count;
static u16 get_unaligned_le16(const void *p) { const u8 *b=p; return b[0] | (u16)b[1]<<8; }
static int device_property_read_string(struct device *d,const char *key,const char **name) {
 assert(!strcmp(key,"firmware-name")); if(property_result)return property_result; *name="private-matched-init"; return 0;
}
static int request_firmware(const struct firmware **fw,const char *name,struct device *d) {
 ++request_calls; if(request_result)return request_result; *fw=&input; return 0;
}
static void release_firmware(const struct firmware *fw) { assert(fw==&input); ++release_calls; }
static int i2c_check_functionality(void *adapter,int flags) { return 1; }
static void *devm_kzalloc(struct device *dev,size_t size,int flags) { assert(!allocated); return allocated=calloc(1,size); }
static struct regulator *devm_regulator_get(struct device *dev,const char *name) { assert(!strcmp(name,"vdd")); ++regulator_lookups; return &supply; }
static int dev_err_probe(struct device *dev,int ret,const char *fmt,...) { return ret; }
static void mutex_init(struct mutex *m) { m->held=false; }
static void mutex_destroy(struct mutex *m) { assert(!m->held); }
static void mutex_lock(struct mutex *m) { assert(!m->held);m->held=true; }
static void mutex_unlock(struct mutex *m) { assert(m->held);m->held=false; }
static void v4l2_i2c_subdev_init(struct v4l2_subdev *sd,struct i2c_client *c,const void *ops) { sd->dev=&c->dev;sd->client=c;c->dev.driver=sd; }
static void *dev_get_drvdata(struct device *dev) { return dev->driver; }
static void *v4l2_get_subdevdata(struct v4l2_subdev *sd) { return sd->client; }
static int i2c_master_send(struct i2c_client *c,const u8 *data,int len) {
 assert(len==2 && i2c_calls<32);memcpy(writes[i2c_calls],data,2);++i2c_calls;
 if(i2c_calls==fail_write_at)
  return fail_write_result;
 return len;
}
static int regulator_enable(struct regulator *r) { ++enable_calls;++r->refs;return 0; }
static int regulator_disable(struct regulator *r) { ++disable_calls;assert(r->refs==1);--r->refs;return 0; }
static void usleep_range(unsigned int low,unsigned int high) { assert(low<=high && sleep_count<32);sleeps[sleep_count++]=low; }
static void v4l2_ctrl_handler_init(struct v4l2_ctrl_handler *h,int count) { h->error=0; }
static struct v4l2_ctrl *v4l2_ctrl_new_std(struct v4l2_ctrl_handler *h,const void *ops,int id,int min,int max,int step,int def) {
 assert(id==V4L2_CID_FOCUS_ABSOLUTE && min==0 && max==1023 && step==1 && def==0);return &focus;
}
static int media_entity_pads_init(struct entity *e,unsigned int count,void *pads) { assert(!count && !pads);return 0; }
static void media_entity_cleanup(struct entity *e) { }
static void v4l2_ctrl_handler_free(struct v4l2_ctrl_handler *h) { }
static void pm_runtime_enable(struct device *d) { ++pm_enable_calls; }
static void pm_runtime_disable(struct device *d) { }
static int v4l2_async_register_subdev(struct v4l2_subdev *sd) { ++registrations;return 0; }
'''
# Add the adapter member without altering any extracted driver function.
preamble = preamble.replace('struct i2c_client { struct device dev; };', 'struct i2c_client { struct device dev; void *adapter; };')
main = r'''
static void reset(const u8 *data,size_t size) {
 free(allocated);allocated=NULL;memset(&client,0,sizeof(client));memset(&supply,0,sizeof(supply));
 property_result=request_result=request_calls=release_calls=0;
 i2c_calls=enable_calls=disable_calls=regulator_lookups=pm_enable_calls=registrations=0;
 fail_write_at=fail_write_result=0;sleep_count=0;memset(writes,0,sizeof(writes));
 input.data=data;input.size=size;
}
static void no_hardware_or_registration(void) {
 assert(!i2c_calls && !enable_calls && !disable_calls && !supply.refs);
 assert(!regulator_lookups && !pm_enable_calls && !registrations);
}
static void invalid(const u8 *data,size_t size,int wanted) {
 reset(data,size);int ret=bu64253_probe(&client);assert(ret==wanted);
 no_hardware_or_registration();assert(request_calls==1 && release_calls==1);
 struct bu64253 *lens=allocated;assert(lens && !lens->init_valid);
 mutex_init(&lens->lock);
 client.dev.driver=&lens->sd;
 assert(bu64253_runtime_resume(&client.dev)==-ENODATA);
 no_hardware_or_registration();
}
static void valid(const u8 *data) {
 reset(data,20);assert(!bu64253_probe(&client));
 struct bu64253 *lens=allocated;assert(lens && lens->init_valid && !lens->target_valid);
 assert(request_calls==1 && release_calls==1 && regulator_lookups==1 && pm_enable_calls==1 && registrations==1);
 assert(!i2c_calls && !enable_calls);
 assert(!bu64253_runtime_resume(&client.dev));
 assert(enable_calls==1 && disable_calls==0 && supply.refs==1 && i2c_calls==3);
 for(int i=0;i<3;i++){assert(!memcmp(writes[i],data+8+i*4,2));assert(sleeps[i+1]==get_unaligned_le16(data+10+i*4));}
 assert(sleeps[0]==10000 && sleep_count==4 && !lens->target_valid);
 mutex_lock(&lens->lock);assert(!bu64253_power_off(lens));mutex_unlock(&lens->lock);
 assert(disable_calls==1 && !supply.refs);
}
static void read_file(const char *path,u8 data[20]) {
 FILE *f=fopen(path,"rb");assert(f);assert(fread(data,1,20,f)==20);assert(fgetc(f)==EOF);assert(!fclose(f));
}
int main(int argc,char **argv) {
 assert(argc==3);u8 first[20],second[20],bad[21];read_file(argv[1],first);read_file(argv[2],second);
 valid(first);valid(second);
 unsigned int invalid_count=0;
 reset(NULL,0);request_result=-ENOENT;assert(bu64253_probe(&client)==-ENOENT);no_hardware_or_registration();assert(request_calls==1&&!release_calls);++invalid_count;
 invalid(first,0,-EINVAL);++invalid_count;
 invalid(first,19,-EINVAL);++invalid_count;
 memcpy(bad,first,20);bad[20]=0;invalid(bad,21,-EINVAL);++invalid_count;
 static const unsigned int changes[][2]={{0,0},{4,2},{5,2},{6,1},{7,1},{8,0xe0},{9,0},{10,0},{12,0xd0},{13,0},{14,0},{16,0xc8},{17,0},{18,0}};
 for(unsigned int i=0;i<sizeof(changes)/sizeof(changes[0]);i++) {
  memcpy(bad,first,20);bad[changes[i][0]]=changes[i][1];invalid(bad,20,-EINVAL);++invalid_count;
 }
 assert(invalid_count==18);
 reset(first,20);property_result=-EINVAL;assert(bu64253_probe(&client)==-EINVAL);no_hardware_or_registration();assert(!request_calls && !release_calls);
 reset(first,20);request_result=-EIO;assert(bu64253_probe(&client)==-EIO);no_hardware_or_registration();assert(request_calls==1 && !release_calls);
 for(int at=1;at<=3;at++) for(int kind=0;kind<2;kind++) {
  reset(first,20);assert(!bu64253_probe(&client));fail_write_at=at;fail_write_result=kind?-ENXIO:1;
  assert(bu64253_runtime_resume(&client.dev)==(kind?-ENXIO:-EIO));
  struct bu64253 *lens=allocated;assert(enable_calls==1 && disable_calls==1 && !supply.refs && !lens->supply_enabled && i2c_calls==at);
 }
 reset(NULL,0);
 printf("INIT_C_RESULT valid=2 invalid=18 extra-missing-property-io=2 init-short-nack=6 power-before-invalid=0 writes-before-invalid=0 result=0\n");
 return 0;
}
'''
code = preamble + definitions + '\n' + block('struct bu64253_init {') + ';\n' + block('struct bu64253 {') + ';\n' + '\n'.join(parts) + '\n' + main
harness = PRIVATE / 'init-c-host-private.c'; harness.write_text(code)
binary = PRIVATE / 'init-c-host-asan'
compile_command = ['gcc', '-std=gnu11', '-g', '-O1', '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                   '-fno-pie', '-no-pie', '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter', str(harness), '-o', str(binary)]
begin = time.monotonic()
attempt = 1
while (PRIVATE / ('init-c-host-compile-r' + str(attempt) + '-private.log')).exists():
    attempt += 1
compile_result = subprocess.run(compile_command, capture_output=True)
(PRIVATE / ('init-c-host-compile-r' + str(attempt) + '-private.log')).write_bytes(compile_result.stdout + compile_result.stderr)
assert compile_result.returncode == 0, (compile_result.stdout + compile_result.stderr).decode()
env = dict(os.environ, ASAN_OPTIONS='detect_leaks=1:abort_on_error=1:strict_string_checks=1', UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
run = subprocess.run([str(binary), str(PRIVATE / 'imx319-bu64253-init.bin'), str(PRIVATE / 's5k3m5sx-bu64253-init.bin')],
                     env=env, capture_output=True, timeout=30)
(PRIVATE / ('init-c-host-run-r' + str(attempt) + '-private.log')).write_bytes(run.stdout + run.stderr)
assert run.returncode == 0 and b'result=0' in run.stdout, (run.returncode, (run.stdout + run.stderr).decode())
report = dict(stage=453, attempt=attempt, scope='actual C load_init/probe with host stubs and bounded init callbacks',
              source_sha256=hashlib.sha256(text.encode()).hexdigest(),
              actual_function_sha256={prefix:hashlib.sha256(part.encode()).hexdigest() for prefix,part in zip(functions, parts)},
              original_c_function_bodies_extracted_without_changes=True, sanitizer='ASAN+UBSAN',
              valid_private_firmware_cases=2, invalid_or_missing_format_cases=18, missing_property_or_io_failure_cases=2,
              invalid_cases_regulator_lookup_pm_registration_power_and_i2c_counts_zero=True,
              runtime_resume_invalid_guard_prevents_power_and_i2c=True,
              valid_resume_writes_exactly_three_matched_init_commands_without_default_dac=True,
              initial_command_short_write_or_nack_cleanup_cases=6,
              real_kernel_pm_framework_or_hardware_tested=False, c_host_compile_exit=compile_result.returncode,
              c_host_run_exit=run.returncode, elapsed_seconds=round(time.monotonic()-begin,3),
              sdk_or_phone_accessed=False, passed=True)
(HERE / ('init-c-r' + str(attempt) + '-validation.json')).write_text(json.dumps(report, indent=2) + '\n')
(HERE / 'init-c-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
