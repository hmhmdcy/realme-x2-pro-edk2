from pathlib import Path
import json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;work=P/'start-observer-regression';work.mkdir(exist_ok=True)
s=(HERE.parent/'kernel370/start-regression.c').read_text()
s=s.replace('struct camss_a5 {','struct camss_a5 {\n void (*failure_snapshot)(struct camss_a5 *a);',1)
s=s.replace('static unsigned consumed,response_count,sends,stops,dumps,clock_order,published_at,stopped_at;', 'static unsigned consumed,response_count,sends,stops,dumps,clock_order,published_at,stopped_at,observations,observed_at;')
anchor='static void publish_start_failure(struct camss_a5 *a) {'
s=s.replace(anchor,'''static void observer(struct camss_a5 *a) {assert(a->lock && a->cpu_release_attempted && backing && a->power_held);++observations;observed_at=++clock_order;}
'''+anchor)
s=s.replace('active=&a;a.resources.sierra=registers;','active=&a;a.failure_snapshot=observer;a.resources.sierra=registers;')
s=s.replace('if(wanted_dumps)assert(published_at && stopped_at>published_at);','if(wanted_dumps)assert(observations==1 && observed_at<published_at && published_at<stopped_at);else assert(!observations);')
after=(P/'camss-icp-a5-boot.c.proposed').read_text();a=after.index('int camss_a5_start(');b=after.index('EXPORT_SYMBOL_GPL(camss_a5_start)',a)
(work/'body.inc').write_text(after[a:b]);(work/'probe.c').write_text(s)
q=subprocess.run(['cc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-misleading-indentation','-fsanitize=address,undefined',str(work/'probe.c'),'-o',str(work/'probe')],capture_output=True);assert not q.returncode,q.stderr.decode()
for case in range(13):
 q=subprocess.run([str(work/'probe'),str(case)],capture_output=True,timeout=10);(work/(str(case)+'-private.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,(case,q.stderr.decode())
report=dict(stage=372,actual_production_start_body=True,tests=13,asan_ubsan=True,platform_and_snapshot_providers_mocked=True,
 observer_runs_under_mutex_before_devcoredump_and_quiesce=True,no_observer_before_cpu_release_or_after_success=True,
 terminal_three_still_rejected_without_sys_init=True,stop_semantics_unchanged_evidence_stage=371,
 not_hardware_snapshot_or_reset_proof=True,phone_operations=False,passed=True)
(HERE/'lifecycle-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
