"""Compile verbatim lifecycle bodies with fault-injected providers, offline only."""
from pathlib import Path
import json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;rows=[]
def run_body(label,probe,body,cases,expected=True):
 work=P/label;work.mkdir(exist_ok=True);(work/'probe.c').write_text(probe);(work/'body.inc').write_text(body)
 q=subprocess.run(['cc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-unused-parameter','-Wno-misleading-indentation','-fsanitize=address,undefined',str(work/'probe.c'),'-o',str(work/'probe')],capture_output=True)
 assert not q.returncode,q.stderr.decode()
 for case in cases:
  q=subprocess.run([str(work/'probe'),str(case)],capture_output=True,timeout=10)
  (work/(str(case)+'-private.log')).write_bytes(q.stdout+q.stderr)
  assert (q.returncode==0)==expected,(label,case,q.stderr.decode()[-1800:])
  rows.append(dict(label=label,case=case,exit_code=q.returncode,expected_pass=expected,matched=True))
before=(P/'camss-icp-a5-boot.c.before').read_text();after=(P/'camss-icp-a5-boot.c.proposed').read_text()
s=(HERE.parent/'kernel368/start-regression.c').read_text().replace('#include "start-method.inc"','#include "body.inc"')
a=s.index('static int stop_locked(');b=s.index('#include "body.inc"',a)
s=s[:a]+'''static int quiesce_locked(struct camss_a5 *a) {
 ++stops;stopped_at=++clock_order;if(stop_error)return stop_error;
 a->cpu_enabled=false;a->irq_enabled=false;a->reset_asserted=true;return 0;
}
static int stop_locked(struct camss_a5 *a) {
 int ret=quiesce_locked(a);if(ret)return ret;a->power_held=false;backing=false;return 0;
}
'''+s[b:]
s=s.replace('else if(scenario!=7)assert(!a.cpu_enabled && !a.power_held && !backing);',
 '''else if(scenario!=7){
  assert(!a.cpu_enabled && !a.irq_enabled && backing && a.reset_asserted);
  assert(a.power_held==(scenario!=10 && scenario!=11));
 }''')
(HERE/'start-regression.c').write_text(s)
def start_body(text):
 a=text.index('int camss_a5_start(');b=text.index('EXPORT_SYMBOL_GPL(camss_a5_start)',a);return text[a:b]
run_body('start-before',s,start_body(before),[2,10],False)
run_body('start-after',s,start_body(after),range(13))
s=(HERE.parent/'kernel368/stop-regression.c').read_text().replace('#include "stop-method.inc"','#include "body.inc"')
s=s.replace('if(scenario==2){reset_error=-EBUSY;expected=-EBUSY;}', 'if(scenario==2 || scenario==8){reset_error=-EBUSY;expected=-EBUSY;}')
s=s.replace('assert(stop_locked(&a)==expected && !a.boot_timer);', '''if(scenario==7){
  assert(quiesce_locked(&a)==0 && backing && a.power_held && !a.cpu_enabled && !a.irq_enabled && a.reset_asserted && !free_tick && !pm_calls);
  assert(quiesce_locked(&a)==0 && backing && a.power_held && !free_tick && !pm_calls);
 }
 assert(stop_locked(&a)==expected && !a.boot_timer);
 if(scenario==8){assert(backing && a.cpu_enabled && a.power_held && !free_tick && !pm_calls);reset_error=0;assert(stop_locked(&a)==0);}''')
(HERE/'stop-regression.c').write_text(s)
a=after.index('static int quiesce_locked(');b=after.index('int camss_a5_stop(',a)
run_body('stop-after',s,after[a:b],range(9))
report=dict(stage=370,verbatim_production_start_quiesce_stop_bodies=True,asan_ubsan=True,
 platform_mmio_reset_dma_pm_and_scheduler_providers_mocked=True,tests=rows,
 failed_start_retains_backing_and_acquired_pm_for_owner=True,reset_failure_retains_cpu_backing_and_pm=True,
 successful_quiesce_does_not_free_unmap_or_release_pm=True,quiesce_and_stop_idempotence_checked=True,
 dma_retirement_still_precedes_pm_release=True,before_source_rejected_by_new_failure_ownership_checks=True,
 no_hardware_quiescence_watchdog_or_firmware_boot_claim=True,phone_operations=False,passed=True)
(HERE/'lifecycle-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
