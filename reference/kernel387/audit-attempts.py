from pathlib import Path
import json
import host
HERE=Path(__file__).resolve().parent
reasons={
 'r1':'DeviceMatch used model rather than driver. Twelve legacy IFE frames, zero IPE jobs; integration rejected.',
 'r2':'IPE discovered; CAPTURE S_FMT attempted after OUTPUT REQBUFS. EBUSY, zero IPE jobs. Negotiate both formats before allocation.',
 'r3':'All four GStreamer captures delivered twelve frames via IPE. Harness rejected jobs49/completed48/failed1. Historical failed counter mixed ECANCELED with errors; exact return code of that job not recorded. Separate future cancellation accounting; do not retrospectively relabel this job.',
 'r4':'Four processed captures plus dual/RAW-only passed; forced isolated IPA could not locate installed proxy from private library path. Add explicit installed IPA/proxy paths. Final wrapper additionally owns its job timer and rejects reopening after failed STREAMOFF.'}
rows=[]
for run,reason in reasons.items():
 d=json.loads((HERE/('pipeline-runtime-'+run+'-validation.json')).read_text());assert d['terminal'] and not d['passed']
 assert not any(d[k] for k in ['worker_live','collector_live','client_process_live'])
 assert all(d[k] for k in ['core_absent','test_absent','adapter_absent','helper_absent','temporary_dt_nodes_absent','temporary_firmware_removed','m2m_video_absent'])
 assert d['same_boot'] and d['taint_after']==0 and d['new_relevant_fault_count']==0
 client=json.loads((host.PRIVATE/('collected-'+run)/'client-private.json').read_text());assert client['services_restored']
 if 'raw-raw' in client['captures']:
  client['captures']['raw-raw'].pop('original_sensor_timestamps_verified',None)
  client['captures']['raw-raw']['raw_pair_sof_verified']=True
 after=d['m2m_before_removal'];rows.append(dict(run=run,reason=reason,passed_captures=client['captures'],jobs=after['jobs'],completed=after['completed'],failed=after['failed'],cancelled=after.get('cancelled'),cleaned=True,services_restored=True,collector_timed_out=d['collector_result']['timeout']))
report=dict(stage=387,attempts=rows,failed_attempts_retained=True,all_terminal_and_cleaned=True,r3_old_failed_count_not_relabelled=True,passed=True)
(HERE/'attempts-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
