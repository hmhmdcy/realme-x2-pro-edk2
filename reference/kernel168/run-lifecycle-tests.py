from pathlib import Path
import json, runpy
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel168')
x=runpy.run_path(str(ref/'test-helpers.py'));out=x['out'];fn=x['function'];run=x['run'];ngd=x['ngd']
common=(ref/'test-lifecycle-stubs.h').read_text()
names=['qcom_slim_ngd_enable','qcom_slim_ngd_down']
before=(out/'source166-rejected-private.patch').read_text()
# The full failed166 source was retained in its earlier patch against163.
baseline=(ref.parent/'kernel166/ngd-pm-lifecycle.patch').read_text()
k=x['k']
source163=(out/'qcom-ngd-ctrl.c.163-before-private').read_text()
extracted=''.join(fn(ngd,n) for n in names)
negative=''.join(fn(source163,n) for n in names)
main='''
int main(void) {
 struct device d={.enabled=true,.suspended=true,.votes=1};
 struct qcom_slim_ngd_ctrl c={.dev=&d,.ctrl={.dev=&d},.state=QCOM_SLIM_NGD_CTRL_DOWN};
 d.data=&c;
 assert(qcom_slim_ngd_enable(&c,true)==0);
 assert(qcom_slim_ngd_enable(&c,true)==0);
 if (registrations!=1 || d.votes!=0) {
  puts("BASELINE_DUPLICATE_UP_REREGISTERS_CONTROLLER");return 2;
 }
 for(int i=0;i<100;i++) {
  drained=false; qcom_slim_ngd_down(&c);
  assert(!c.registered && c.state==QCOM_SLIM_NGD_CTRL_DOWN && d.votes==1);
  assert(drained && dma_exits==i+1 && unregisters==i+1);
  qcom_slim_ngd_down(&c); assert(unregisters==i+1 && d.votes==1);
  assert(qcom_slim_ngd_enable(&c,true)==0);
  assert(c.registered && c.state==QCOM_SLIM_NGD_CTRL_AWAKE && d.votes==0);
  assert(qcom_slim_ngd_enable(&c,true)==0 && registrations==i+2);
 }
 assert(registrations==101 && unregisters==100 && dma_exits==100 && drains==100);
 printf("{\\"cycles\\":100,\\"registrations\\":101,\\"unregisters\\":100}\\n");return 0;
}
'''
control=run('lifecycle-baseline',common+negative+main,2)
result=json.loads(run('lifecycle-candidate',common+extracted+main))
report=json.loads((ref/'host-tests-validation.json').read_text())
report.update(lifecycle=result,lifecycle_negative_control=control,
              master_work_drain_and_lock_order_checked_in_primitive_stubs=True,
              true_kernel_scheduler_interleavings_not_proven_by_host_tests=True)
for folder in [ref,out]: (folder/'host-tests-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(result))
