from pathlib import Path
import json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;work=P/'ownership-regression';work.mkdir(exist_ok=True)
after=(HERE/'camss-icp-a5-boot-test.c').read_text();before=after.replace(' &&\n\t    !device_a5->resources.enabled_groups && !device_a5->resources.held_domains','').replace(' ||\n\t     a5->resources.enabled_groups || a5->resources.held_domains','')
prefix='''#include <assert.h>
#include <stdbool.h>
#include <stdlib.h>
#include <errno.h>
struct camss_a5 {struct {unsigned enabled_groups,held_domains;} resources;bool backing,cpu_enabled,power_held;};
static struct camss_a5 *device_a5;
static bool pinned;
static int stop_error;static unsigned gets,puts;
#define THIS_MODULE ((void *)1)
static int camss_a5_stop(struct camss_a5 *a){(void)a;return stop_error;}
static bool camss_a5_backing_owned(struct camss_a5 *a){return a->backing;}
static void module_put(void *m){assert(m==THIS_MODULE);++puts;}
static void __module_get(void *m){assert(m==THIS_MODULE);++gets;}
'''
main='''int main(int argc,char **argv){assert(argc==2);unsigned which=atoi(argv[1]);struct camss_a5 a={0};device_a5=&a;
if(which==1)a.resources.enabled_groups=1;
if(which==2)a.resources.held_domains=1;
if(which==3)a.power_held=true;
if(which==4)a.backing=true;
if(which==5)a.cpu_enabled=true;
if(which==6)stop_error=-EIO;
if(which==7){a.resources.enabled_groups=1;a.resources.held_domains=1;}
pin_after_start(&a);assert(pinned==(which!=0 && which!=6));assert(gets==(unsigned)pinned);
pinned=true;assert(cleanup()==stop_error);assert(pinned==(which!=0));assert(puts==(which==0));
return 0;}
'''
rows=[]
for label,s,cases in [('before',before,[1,2]),('after',after,range(8))]:
 a=s.index('static int cleanup(void)');b=s.index('static ssize_t cleanup_store',a);cleanup=s[a:b]
 a=s.index('\tif ((camss_a5_backing_owned(a5)');b=s.index('\n\tif (!ret && a5->pc_error)',a);pin=s[a:b]
 (work/'probe.c').write_text(prefix+cleanup+'\nstatic void pin_after_start(struct camss_a5 *a5){\n'+pin+'\n}\n'+main)
 q=subprocess.run(['cc','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(work/'probe.c'),'-o',str(work/'probe')],capture_output=True);assert not q.returncode,q.stderr.decode()
 for case in cases:
  q=subprocess.run([str(work/'probe'),str(case)],capture_output=True,timeout=10);(P/f'ownership-{label}-{case}-private.log').write_bytes(q.stdout+q.stderr)
  assert (q.returncode==0)==(label=='after'),(label,case,q.stderr.decode()[-1500:])
  rows.append(dict(source=label,case=case,exit_code=q.returncode,matched=True))
report=dict(stage=369,actual_cleanup_function_and_pin_condition=True,provider_calls_mocked=True,asan_ubsan=True,
    remaining_clock_or_domain_ownership_prevents_unload=True,only_fully_released_owner_unpinned=True,tests=rows,passed=True)
(HERE/'ownership-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
