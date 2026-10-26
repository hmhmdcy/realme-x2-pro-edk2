"""Exercise the exact held-failure decision and module pin, with cleanup injected."""
from pathlib import Path
import json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;work=P/'owner-regression';work.mkdir(exist_ok=True)
s=(P/'camss-icp-a5-boot-test.c.proposed').read_text();a=s.index('done:\n\tif (ret && hold_start_failure');b=s.index('\n\tif (!ret && a5->pc_error)',a)
body=s[a+len('done:\n'):b]
prefix='''#include <assert.h>
#include <stdbool.h>
#include <stdlib.h>
#include <errno.h>
#include <string.h>
struct camss_a5 {
 bool cpu_release_attempted,cpu_enabled,irq_enabled,reset_asserted,power_held;
 int cleanup_error;bool backing;
 struct {void *cpu;unsigned bytes,mapped;} firmware;
 struct {unsigned enabled_groups,held_domains;} resources;
};
static bool hold_start_failure,held_failure,pinned;static const char *phase="start";
static unsigned stops,gets;static int stop_error;
#define THIS_MODULE ((void *)1)
static int cleanup(void) {++stops;return stop_error;}
static bool camss_a5_backing_owned(struct camss_a5 *a) {return a->backing;}
static void __module_get(void *m) {assert(m==THIS_MODULE);++gets;}
static int done(struct camss_a5 *a5,int ret) {int stop;
'''
main='''return ret;}
int main(int argc,char **argv) {
 assert(argc==2);unsigned scenario=atoi(argv[1]);
 struct camss_a5 a={.cpu_release_attempted=true,.reset_asserted=true,.power_held=true,.backing=true,.firmware={(void *)1,64,64}};
 int ret=-EREMOTEIO;hold_start_failure=true;
 switch(scenario) {
 case 0:hold_start_failure=false;break;
 case 2:a.cpu_enabled=true;break;
 case 3:a.irq_enabled=true;break;
 case 4:a.reset_asserted=false;break;
 case 5:a.power_held=false;break;
 case 6:a.firmware.cpu=NULL;break;
 case 7:a.firmware.mapped=63;break;
 case 8:a.cpu_release_attempted=false;break;
 case 9:a.cleanup_error=-EIO;break;
 case 10:ret=0;break;
 case 11:stop_error=-EIO;hold_start_failure=false;a.backing=false;a.power_held=false;a.resources.enabled_groups=1;break;
 case 12:stop_error=-EIO;hold_start_failure=false;a.backing=false;a.power_held=false;a.resources.held_domains=1;break;
 }
 assert(done(&a,ret)==(stop_error?stop_error:ret));
 assert(held_failure==(scenario==1));assert(stops==(scenario==1?0U:1U));
 assert(pinned && gets==1);if(scenario==1)assert(!strcmp(phase,"failed-held"));
 return 0;
}
'''
(work/'probe.c').write_text(prefix+body+main)
q=subprocess.run(['cc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(work/'probe.c'),'-o',str(work/'probe')],capture_output=True);assert not q.returncode,q.stderr.decode()
rows=[]
for case in range(13):
 q=subprocess.run([str(work/'probe'),str(case)],capture_output=True,timeout=10);(work/(str(case)+'-private.log')).write_bytes(q.stdout+q.stderr)
 assert not q.returncode,(case,q.stderr.decode());rows.append(dict(case=case,passed=True))
report=dict(stage=370,actual_probe_hold_and_pin_decision=True,asan_ubsan=True,cleanup_and_module_providers_mocked=True,
 tests=rows,hold_is_opt_in_and_requires_failed_start_cpu_release_and_successful_quiesce=True,
 reset_or_partial_mapping_failures_do_not_expose_snapshot=True,clock_domain_leftovers_still_pin_owner=True,
 no_actual_hardware_or_module_unload_claim=True,phone_operations=False,passed=True)
(HERE/'owner-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='tests'},indent=2))
