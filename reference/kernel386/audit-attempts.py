"""Keep pre-firmware observer failures distinct from the passing m2m run."""
from pathlib import Path
import json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;rows=[]
for i in range(1,5):
 d=json.loads((HERE/(f'm2m-runtime-r{i}-validation.json')).read_text())
 assert d['terminal'] and d['same_boot'] and not any(d[k] for k in ['worker_live','collector_live','client_process_live'])
 assert all(d[k] for k in ['core_absent','test_absent','adapter_absent','helper_absent','m2m_video_absent','temporary_dt_nodes_absent','temporary_firmware_removed'])
 assert d['taint_after']==0 and d['new_relevant_fault_count']==0 and d['clocks_after']==d['clocks_before']
 row=dict(run='r'+str(i),passed=d['passed'],cpu_release_attempted=d['device_result']['cpu_release_attempted'],
  client_started='client_exit' in d,terminal_and_all_processes_exited=True,resources_released=True)
 if i<4:
  assert not d['passed'] and not d['device_result']['cpu_release_attempted'] and d['device_result']['frames_completed']==0
  row['failure']=d['error']
  if 'ready_result' in d:row['probe_saved_resource_groups']=d['ready_result']['remaining_groups']
 else:
  state=json.loads((P/'observation-r4-private.json').read_text())['state']
  row.update(stale_probe_groups=state['probe_snapshot_before_refresh']['remaining_groups'],
   refreshed_groups=state['ready_result']['remaining_groups'],refreshed_pm_status=state['ready_pm_status'],
   old_saved_snapshot_not_used_as_current_ownership=True)
  assert d['passed'] and state['ready_pm_status']=='suspended' and not state['ready_result']['remaining_groups']
 rows.append(row)
report=dict(stage=386,attempts=rows,failed_runs_did_not_start_firmware_or_submit_images=True,
 media_nodes_on_media_bus_not_media_class_verified=True,saved_probe_state_refreshed_after_registration=True,
 passing_run_used_unchanged_modules_after_observer_repairs=True,passed=True)
(HERE/'attempts-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
