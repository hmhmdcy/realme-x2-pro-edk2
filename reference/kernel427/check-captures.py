"""Distinguish delivered FULL frames, partial DS4 DMA, and failed feature tests."""
from pathlib import Path
import json,re
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;rows=[]
for attempt in range(1,9):
 d=json.loads((P/('capture-observe-r'+str(attempt)+'-private.json')).read_text());s=d['state']
 assert s['terminal'] and not d['worker_live'] and not d['client_live']
 assert s['formal_modules_restored'] and s['services_restored'] and s['taint_after']==s['taint_before']==512 and not s.get('cleanup_failure')
 assert not s['passed'] and s['failure']
 assert s['after_status']['jobs']==s['after_status']['completed']==s['after_status']['failed']==s['after_status']['cancelled']==0
 assert s['after_status']['owner_refs']==53 and not any(s['after_core'][k] for k in ['backing_owned','cpu_enabled','irq_enabled','power_held','mapped_bytes','ipe_dma_pending','imported_buffers'])
 rows.append(dict(attempt=attempt,experiment_passed=False,captures=s['captures'],formal_modules_and_services_restored=True,taint_unchanged=True))
root=P/'capture-collected-r8';text=(root/'pattern/capture.log').read_text();sofs=[int(x) for x in re.findall(r'^SOF sequence=(\d+)$',text,re.M)]
assert len(sofs)>100 and not re.search(r'^FRAME ',text,re.M)
undelivered=[dict(re.findall(r'([a-z_]+)=([^ ]+)',line)) for line in text.splitlines() if line.startswith('UNDELIVERED ')]
coarse=next(r for r in undelivered if r['kind']=='ds4' and r['index']=='0');assert int(coarse['changed_rows'])==4 and int(coarse['last_row'])==3
raw=(root/'pattern/undelivered-ds4-0.bin').read_bytes();assert len(raw)==46080
def changed(at):return raw[at]!=(0xa5^((at*197+(at>>8)*31)&255))
assert not any(changed(i) for i in range(4*768,len(raw)))
kernel=(root/'kernel-log-private.txt').read_text();statuses=[(int(a,16),int(b,16)) for a,b in re.findall(r'DS4 bringup irq top=([0-9a-f]+)/([0-9a-f]+)',kernel)]
seen=0
for top0,top1 in statuses:seen|=top1&0xefff7e80
assert seen==0x1800
full=(root/'full-only/capture.log').read_text();assert len(re.findall(r'^FRAME kind=full ',full,re.M))==24 and 'DS4_RESULT result=0' in full
r=dict(stage=427,validation_scope='Evidence consistency and restoration; DS4 feature test failed',attempts=rows,
 latest_physical_camss_sha256='b5b94ec927765f0ca007696fd89d53d37d1386ffdd2c941d6d7f202704df466d',
 ds4_valid_complete_frame_count=0,ds4_partial_dma_observed=True,partial_packed_rows=4,partial_rows_not_counted_as_images=True,
 full_only_control_frames=24,simultaneous_full_ds4_delivered_frames=0,sof_observations=len(sofs),
 original_oem_camif_error_mask='0xefff7e80',hardware_error_status1_seen=hex(seen),hardware_overflow_classification_from_oem_driver=True,
 no_new_smmu_fault_or_kernel_warning_messages=True,absence_of_kernel_fault_messages_does_not_mean_no_hardware_errors=True,
 last_successful_scene_stage=424,scene_case_not_reached=True,ipe_jobs_submitted_this_stage=0,
 first_module_reload_reset_per_lifetime_counters_from_793_to_zero=True,counter_reset_not_a_failed_ipe_job=True,
 formal_modules_services_and_resources_restored=True,complete_ds4_dma_verified=False,complete_automatic_tmc_ltm_chain_verified=False,passed=True)
(HERE/'hardware-investigation-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='attempts'},indent=2))
