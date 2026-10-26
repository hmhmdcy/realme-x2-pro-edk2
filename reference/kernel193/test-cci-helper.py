from pathlib import Path
import subprocess,json,hashlib,os
ref=Path(__file__).resolve().parent;out=Path('/mnt/e/edk2-samurai-out/kernel193');source=(ref/'samurai-cci-bringup.c').read_text()
body='\n'.join(l for l in source.splitlines() if not l.startswith('#include'))
stub=r'''
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <stdlib.h>
#define EPROBE_DEFER 517
#define __init
#define __exit
#define OF_POPULATED 1
#define module_init(x)
#define module_exit(x)
#define MODULE_DESCRIPTION(x)
#define MODULE_AUTHOR(x)
#define MODULE_LICENSE(x)
struct of_changeset { int initialized; };
struct device_node { int refs; };
struct device { int refs; };
struct platform_device { struct device dev; };
static struct device_node node;
static struct platform_device pdev;
static int scenario, finds, destroyed, reverts, errors;
static bool available;
static int of_machine_is_compatible(const char *name) { (void)name;return scenario!=1; }
static struct device_node *of_find_node_by_path(const char *path) { (void)path;if(scenario==2)return NULL;node.refs++;return &node; }
static int of_device_is_compatible(struct device_node *np,const char *s) { (void)np;(void)s;return scenario!=3; }
static int of_property_read_string(struct device_node *np,const char *n,const char **s) { (void)np;(void)n;*s=scenario==5?"okay":"disabled";return scenario==4?-EINVAL:0; }
static int of_node_check_flag(struct device_node *np,int flag) { (void)np;(void)flag;return scenario==6; }
static struct platform_device *of_find_device_by_node(struct device_node *np) { (void)np;finds++;if((finds==1&&scenario==7)||(finds==2&&scenario!=12)){pdev.dev.refs++;return &pdev;}return NULL; }
static void platform_device_put(struct platform_device *p) { if(--p->dev.refs<0)abort(); }
static void of_node_put(struct device_node *np) { if(--np->refs<0)abort(); }
static void of_changeset_init(struct of_changeset *cs) { cs->initialized=1; }
static int of_changeset_update_prop_string(struct of_changeset *cs,struct device_node *np,const char *p,const char *s) { (void)cs;(void)np;(void)p;(void)s;return scenario==8?-ENOMEM:0; }
static int of_changeset_apply(struct of_changeset *cs) { (void)cs;available=scenario!=9&&scenario!=11;return scenario==9||scenario==10?-EINVAL:0; }
static int of_device_is_available(struct device_node *np) { (void)np;return available; }
static int of_changeset_revert(struct of_changeset *cs) { (void)cs;reverts++;if(scenario==15)return -EIO;available=false;return 0; }
static void of_changeset_destroy(struct of_changeset *cs) { if(!cs->initialized)abort();cs->initialized=0;destroyed++; }
static int device_is_bound(struct device *d) { (void)d;return scenario!=13; }
#define dev_info(...) ((void)0)
#define pr_err(...) (errors++)
'''
main=r'''
int main(void) {
 int expected[]={0,-ENODEV,-ENODEV,-EBUSY,-EBUSY,-EBUSY,-EBUSY,-EBUSY,-ENOMEM,-EINVAL,-EINVAL,-EIO,-ENODEV,-EPROBE_DEFER,0,0};
 for(scenario=0;scenario<16;scenario++) {
  finds=destroyed=reverts=errors=0;available=false;node.refs=pdev.dev.refs=0;applied=false;
  int rc=samurai_cci_bringup_init();
  if(rc!=expected[scenario]||node.refs||pdev.dev.refs) return 1;
  if(!rc)samurai_cci_bringup_exit();
  int expect_destroy=scenario==0||scenario>=8;
  int expect_revert=scenario==0||scenario==10||scenario==12||scenario==13||scenario>=14;
  if(destroyed!=expect_destroy||reverts!=expect_revert) return 2;
  if((scenario==15)!=(errors==1)) return 3;
  if(scenario!=15&&available) return 4;
 }
 puts("16 real init/exit control-flow scenarios passed");return 0;
}
'''
c=out/'cci-helper-host-private.c';c.write_text(stub+body+main);exe=out/'cci-helper-host-private'
subprocess.run(['gcc','-std=c11','-Wall','-Wextra','-Werror','-g','-O1','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(c),'-o',str(exe)],check=True,capture_output=True)
run=subprocess.run([str(exe)],capture_output=True,text=True,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=1:abort_on_error=1',UBSAN_OPTIONS='halt_on_error=1'));(out/'cci-helper-host-tests-private.log').write_text(run.stdout+run.stderr);assert run.returncode==0 and not run.stderr,(run.returncode,run.stderr)
record=dict(stage=193,source_sha256=hashlib.sha256(source.encode()).hexdigest(),actual_init_exit_functions_executed=True,scenarios=16,asan_ubsan_passed=True,apply_notifier_failure_after_property_update_reverted=True,reference_balance_checked=True,revert_failure_reported=True,hardware_access=False)
(ref/'cci-helper-host-validation.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
