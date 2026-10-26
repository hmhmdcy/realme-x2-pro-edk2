from pathlib import Path
import json,shutil,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;work=P/'stop-regression';work.mkdir(exist_ok=True)
shutil.copyfile(HERE/'stop-regression.c',work/'probe.c');rows=[]
for label,path,cases in [('before',P/'boot-before-private.c',[0,1]),('after',P/'boot-proposed.c',range(7))]:
 s=path.read_text();a=s.index('static int stop_locked(');b=s.index('int camss_a5_stop(',a);(work/'stop-method.inc').write_text(s[a:b])
 q=subprocess.run(['cc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-misleading-indentation','-fsanitize=address,undefined',str(work/'probe.c'),'-o',str(work/'probe')],capture_output=True)
 assert not q.returncode,q.stderr.decode()
 for case in cases:
  q=subprocess.run([str(work/'probe'),str(case)],capture_output=True,timeout=10);(P/f'stop-{label}-{case}-private.log').write_bytes(q.stdout+q.stderr)
  assert (q.returncode==0)==(label=='after'),(label,case,q.stderr.decode()[-2000:])
  rows.append(dict(source=label,case=case,exit_code=q.returncode,matched=True))
report=dict(stage=368,verbatim_production_stop_body=True,asan_ubsan=True,mmio_reset_dma_and_pm_providers_mocked=True,
    dma_alias_retirement_precedes_supplier_powerdown=True,failed_unmap_keeps_backing_and_pm_ownership_for_retry=True,
    failed_reset_keeps_cpu_memory_and_pm_ownership=True,pm_usage_reference_not_dropped_twice=True,
    actual_smmu_quiescence_or_watchdog_cause_not_proven=True,tests=rows,passed=True)
(HERE/'stop-regression-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
