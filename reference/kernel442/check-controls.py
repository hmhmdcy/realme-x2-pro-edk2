"""Summarize retained callback controls; do not infer a steady backlog fix."""
from pathlib import Path
import contextlib,io,json,re,runpy,sys
import host
HERE=Path(__file__).resolve().parent
probe=json.loads((HERE/'client-build-validation.json').read_text())['clients'][0]['sha256']
rows=[]
for attempt in ['r1','r3','r4','r5','r6','r7','r8']:
 sys.argv=[str(HERE/'analyze-probe.py'),attempt]
 with contextlib.redirect_stdout(io.StringIO()):runpy.run_path(str(HERE/'analyze-probe.py'),run_name='__main__')
 timing=json.loads((HERE/f'callback-timing-{attempt}-validation.json').read_text())
 staged=json.loads((HERE/f'runtime-staging-{attempt}-validation.json').read_text())
 assert staged['passed']
 if attempt!='r1':assert staged['capture_sha256']==probe
 root=host.PRIVATE/('runtime-collected-'+attempt)
 state=json.loads((root/'state.json').read_text());text=(root/'1280x720-isolated/client.log').read_text()
 assert state['terminal'] and state['formal_modules_restored'] and state['services_restored']
 assert state['taint_before']==state['taint_after']==0 and not state['new_faults']
 mode=re.findall(r'CAPTURE_MODE queued=(\d+) injected-delay-ms=(\d+)',text)
 queued,delay=map(int,mode[0]) if mode else (0,0)
 frames=re.findall(r'ADAPT_FRAME ',text)
 successful=len([p for p in (root/'1280x720-isolated').glob('frame-*.nv12') if p.stat().st_size==1382400])
 if attempt=='r3':
  assert not state['passed'] and successful==50 and len(frames)==53 and not timing['pipeline_changed']
 else:assert state['passed'] and timing['capture_succeeded'] and successful==len(frames)
 rows.append(dict(attempt=attempt,queued=bool(queued),first_frame_delay_ms=delay,
  delivered_successful_images=successful,application_frame_callbacks=len(frames),
  runtime_passed=state['passed'],pipeline_changed=timing['pipeline_changed'],
  event_queue_peak=timing['app_event_queue_peak'],copy_and_luma=timing['copy_and_luma'],
  file_write=timing['file_write'],formal_restored=True,new_kernel_faults=0))
out=dict(stage=442,rows=rows,same_probe_binary_for_r3_through_r8=True,
 injected_pause_only_before_first_frame=True,steady_backlog_root_cause_closed=False,
 queued_probe_follows_existing_cam_app_dispatch=True,
 actual_pipeline_fix_is_stop_cancellation_only=True,passed=True)
(HERE/'callback-controls-validation.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
