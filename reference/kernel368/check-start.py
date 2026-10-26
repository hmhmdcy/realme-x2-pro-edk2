"""Compile actual start bodies; exercise terminal errors and dump-before-stop."""
from pathlib import Path
import json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;work=P/'start-regression';work.mkdir(exist_ok=True)
s=(HERE.parent/'kernel364/hfi-start-regression.c').read_text()
s=s.replace('static unsigned consumed,response_count,sends,stops;','static unsigned consumed,response_count,sends,stops,dumps,clock_order,published_at,stopped_at;')
s=s.replace('static bool backing;','static bool backing;\nstatic int prepare_error,resume_error,stop_error;')
s=s.replace('backing=true;return 0;}','backing=true;return prepare_error;}')
s=s.replace('(void)dev;return 0;}','(void)dev;return resume_error;}',1)
a=s.index('static int stop_locked(');b=s.index('#include "start-method.inc"',a)
s=s[:a]+'''static void publish_start_failure(struct camss_a5 *a) {
 if(a->cpu_release_attempted){++dumps;published_at=++clock_order;}
}
static int stop_locked(struct camss_a5 *a) {
 ++stops;stopped_at=++clock_order;if(stop_error)return stop_error;
 a->cpu_enabled=false;a->power_held=false;a->irq_enabled=false;backing=false;return 0;
}
'''+s[b:]
a=s.index('int main(')
s=s[:a]+'''int main(int argc,char **argv)
{
 assert(argc==2);int scenario=atoi(argv[1]);struct camss_a5 a={0};struct firmware fw={0};active=&a;a.resources.sierra=registers;registers[A5_FW_VERSION/4]=0x01000100;
 response_count=1;responses[0]=1;int expected=0;unsigned wanted_sends=1,wanted_dumps=0;
 if(scenario==1){response_count=3;responses[0]=0;responses[1]=3;responses[2]=1;expected=-EREMOTEIO;wanted_sends=0;wanted_dumps=1;}
 if(scenario==2){responses[0]=3;expected=-EREMOTEIO;wanted_sends=0;wanted_dumps=1;}
 if(scenario==3){responses[0]=2;expected=-EREMOTEIO;wanted_sends=0;wanted_dumps=1;}
 if(scenario==4){responses[0]=0;expected=-ETIMEDOUT;wanted_sends=0;wanted_dumps=1;}
 if(scenario==5){responses[0]=3;expire_after=0;expected=-ETIMEDOUT;wanted_sends=0;wanted_dumps=1;}
 if(scenario==6){command_error=-EIO;expected=-EIO;wanted_dumps=1;}
 if(scenario==7){a.cpu_enabled=true;expected=-EBUSY;wanted_sends=0;}
 if(scenario==8){responses[0]=4;expected=-ETIMEDOUT;wanted_sends=0;wanted_dumps=1;}
 if(scenario==9){response_count=3;responses[0]=0;responses[1]=4;responses[2]=1;}
 if(scenario==10){resume_error=-EIO;expected=-EIO;wanted_sends=0;}
 if(scenario==11){prepare_error=-EINVAL;expected=-EINVAL;wanted_sends=0;}
 if(scenario==12){responses[0]=3;stop_error=-EBUSY;expected=-EREMOTEIO;wanted_sends=0;wanted_dumps=1;}
 assert(camss_a5_start(&a,&fw)==expected);assert(!a.lock && !a.boot_timer);
 assert(sends==wanted_sends && dumps==wanted_dumps);
 assert(stops==((expected && scenario!=7)?1U:0U));
 if(wanted_dumps)assert(published_at && stopped_at>published_at);
 if(scenario==1)assert(consumed==2);
 if(scenario==2)assert(consumed==1);
 if(scenario==12)assert(backing && a.cpu_enabled && a.power_held && a.cleanup_error==-EBUSY);
 else if(!expected)assert(a.initialized && a.cpu_enabled && a.power_held);
 else if(scenario!=7)assert(!a.cpu_enabled && !a.power_held && !backing);
 puts("A5_START_DUMP_PASS");
}
'''
(HERE/'start-regression.c').write_text(s);(work/'probe.c').write_text(s)
rows=[]
for label,path,cases in [('before',P/'boot-before-private.c',[1,2]),('after',P/'boot-proposed.c',range(13))]:
 text=path.read_text();a=text.index('int camss_a5_start(');b=text.index('EXPORT_SYMBOL_GPL(camss_a5_start)',a)
 (work/'start-method.inc').write_text(text[a:b])
 q=subprocess.run(['cc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-misleading-indentation','-fsanitize=address,undefined',str(work/'probe.c'),'-o',str(work/'probe')],capture_output=True)
 assert not q.returncode,q.stderr.decode()
 for case in cases:
  q=subprocess.run([str(work/'probe'),str(case)],capture_output=True,timeout=10);(P/f'start-{label}-{case}-private.log').write_bytes(q.stdout+q.stderr)
  assert (q.returncode==0)==(label=='after'),(label,case,q.stderr.decode()[-2000:])
  rows.append(dict(source=label,case=case,exit_code=q.returncode,matched=True))
report=dict(stage=368,verbatim_production_start_body=True,platform_and_cleanup_providers_mocked=True,asan_ubsan=True,
    fatal_three_returns_remoteio_without_sys_init=True,fault_not_hidden_by_later_ready=True,
    dump_attempt_precedes_cleanup=True,no_dump_before_cpu_release=True,failed_cleanup_retains_resources=True,
    watchdog_fix_or_hardware_boot_not_claimed=True,tests=rows,passed=True)
(HERE/'start-regression-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
