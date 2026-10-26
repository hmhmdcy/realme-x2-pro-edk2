"""Exercise production stop/PM bodies; providers are mocks, not hardware proof."""
from pathlib import Path
import json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;rows=[]
for label,suffix,cases,expected in [('old','.before',[0],False),('new','.proposed',range(13),True)]:
 text=(P/('camss-icp-a5-boot.c'+suffix)).read_text()
 a=text.index('static int quiesce_locked(');b=text.index('int camss_a5_stop(',a);body=text[a:b]
 a=text.index('int camss_a5_runtime_suspend(');b=text.index('EXPORT_SYMBOL_GPL(camss_a5_runtime_suspend)',a)
 body+=text[a:b].replace('int camss_a5_runtime_suspend(', 'static int camss_a5_runtime_suspend(')
 work=P/('stop-model-'+label);work.mkdir(exist_ok=True);(work/'body.inc').write_text(body);(work/'probe.c').write_text((HERE/'stop-regression.c').read_text())
 q=subprocess.run(['cc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-unused-parameter','-fsanitize=address,undefined',str(work/'probe.c'),'-o',str(work/'probe')],capture_output=True);assert not q.returncode,q.stderr.decode()
 for case in cases:
  q=subprocess.run([str(work/'probe'),str(case)],capture_output=True,timeout=10);(work/(str(case)+'-private.log')).write_bytes(q.stdout+q.stderr)
  assert (q.returncode==0)==expected,(label,case,q.stderr.decode()[-1600:]);rows.append(dict(source=label,case=case,expected_pass=expected,matched=True))
report=dict(stage=375,actual_production_quiesce_stop_runtime_suspend_bodies=True,asan_ubsan=True,tests=rows,
 cooperative_stop_and_normal_runtime_suspend_do_not_assert_block_reset=True,pc_or_wfi_or_control_readback_failure_forces_reset=True,
 forced_reset_failure_retains_cpu_backing_pm=True,unmap_failure_retains_backing_pm=True,dma_retired_before_pm_suspend=True,
 quiesce_idempotent_and_does_not_free_dma_or_pm=True,mmio_irq_dma_reset_pm_providers_mocked=True,phone_operations=False,passed=True)
(HERE/'stop-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='tests'},indent=2))
