"""Audit normal consumer frames, source receipts, and timestamp cadence."""
from pathlib import Path
import importlib.util,json,re,statistics,sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('frame443',HERE/'frame-audit.py');audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
attempt=sys.argv[1] if len(sys.argv)>1 else 'r1';root=P/('runtime-collected-'+attempt)
state=json.loads((root/'state.json').read_text());assert state['terminal'] and state['passed'] and not state['failure'] and not state['new_faults']
assert state['formal_modules_restored'] and state['services_restored'] and state['taint_before']==state['taint_after']==0
assert set(state['captures'])=={f'{w}x{h}-{k}' for w,h in [(1280,720),(1920,1080)] for k in ['native','isolated']}
staged=json.loads((HERE/f'runtime-staging-{attempt}-validation.json').read_text())
assert staged['core_sha256']=='f7c25ff3818b95954cfe7cc310d21f3b406225860abf20bb44e32ee66f5ad704'
assert staged['profile_sha256']==json.loads((HERE/'profile-export-validation.json').read_text())['profile_sha256']
rows=[];completed=0;plugins=set()
for name,summary in state['captures'].items():
 text=(root/name/'client.log').read_text();w=summary['width'];h=summary['height']
 assert summary['mapped_candidate_core'] and summary['actual_sensor']==[4608,2592]
 samples=[tuple(map(int,m)) for m in re.findall(r'GST_IMAGE frame=(\d+) width=(\d+) height=(\d+) bytes=(\d+) pts=(\d+) hash=(\d+) sequence=(\d+) wall-ns=(\d+)',text)]
 assert len(samples)==120 and [s[0] for s in samples]==list(range(120))
 assert all(s[1:4]==(w,h,w*h*3//2) and s[5]>0 for s in samples)
 assert all(b[4]>a[4] and b[6]>a[6] and b[7]>a[7] for a,b in zip(samples,samples[1:]))
 app={int(p) for p in re.findall(r'APPLICATION_PROCESS pid=(\d+)',text)};ipa={int(p) for p in re.findall(r'IPA stats pid=(\d+)',text)}
 assert len(app)==len(ipa)==1 and bool(app&ipa)==(not summary['isolated'])
 row=audit.audit_gst(text,'s5kgw1',width=w,height=h,stride=w,coarse_bytes=summary['coarse_bytes'])
 assert row['queued_images']==summary['ipe_completed']
 intervals=[(b[4]-a[4])/1e6 for a,b in zip(samples[8:],samples[9:])]
 wall_intervals=[(b[7]-a[7])/1e6 for a,b in zip(samples[8:],samples[9:])]
 dt=samples[-1][4]-samples[8][4];dw=samples[-1][7]-samples[8][7]
 row.update(capture=name,actual_sensor=[4608,2592],consumer='libcamerasrc/appsink',
  timestamp_fps=round((len(samples)-9)*1e9/dt,3),wall_fps=round((len(samples)-9)*1e9/dw,3),
  median_pts_interval_ms=round(statistics.median(intervals),3),maximum_pts_interval_ms=round(max(intervals),3),
  maximum_wall_interval_ms=round(max(wall_intervals),3),
  kernel_sequence_gaps=sum(b[6]-a[6]-1 for a,b in zip(samples,samples[1:])),
  stop_cancel_requests=text.count('REQUEST_STOP_CANCEL '))
 assert row['stop_cancel_requests']>0;rows.append(row);completed+=summary['ipe_completed'];plugins.add(summary['plugin_sha256'])
s=state['candidate_final_status'];assert s['jobs']==s['completed']==s['direct_completed']==completed
assert not any(s[k] for k in ['users','running','failed','cancelled','first_error','fatal','pinned','orphans'])
assert len(plugins)==1
kernel=(root/'kernel-log-private.txt').read_text();assert kernel.count('A5 IPE frame completed request=')==completed
r=dict(stage=443,attempt=attempt,rows=rows,total_ipe_completed=completed,
 unchanged442_core_and_441_modules=True,only_mode4_ds4_profile_binding_added=True,
 factory_profile_and_actual_ipa5_proofs=True,normal_gstreamer_consumer=True,
 historical441_backlog_root_cause_closed=False,target30fps_accepted=False,
 formal440_restored=True,new_kernel_faults=0,taint=0,installed=False,full_goal_complete=False,passed=True)
(HERE/'hardware-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
