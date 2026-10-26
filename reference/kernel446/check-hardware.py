"""Audit source receipts separately from consumers, including AF move fallback."""
from pathlib import Path
import ast,importlib.util,json,re,statistics,sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
auto=module('auto441',HERE.parent/'kernel441/frame-audit.py');gst=module('gst443',HERE.parent/'kernel443/frame-audit.py')
join_source=(HERE.parent/'kernel442/check-full.py').read_text()
node=next(n for n in ast.parse(join_source).body if isinstance(n,ast.FunctionDef) and n.name=='join_split_frame_record')
exec(ast.get_source_segment(join_source,node))
attempt=sys.argv[1] if len(sys.argv)>1 else 'r1';root=P/('runtime-collected-'+attempt)
state=json.loads((root/'state.json').read_text());assert state['terminal'] and state['passed'] and not state['failure'] and not state['new_faults']
assert state['formal_modules_restored'] and state['services_restored'] and state['taint_before']==state['taint_after']==0
staged=json.loads((HERE/f'runtime-staging-{attempt}-validation.json').read_text())
build=json.loads((HERE/'build-validation.json').read_text())
assert staged['core_sha256']==next(r['sha256'] for r in build['runtime_files'] if r['name']=='libcamera.so.0.7.2') and staged['private_ipa_version']==6
assert staged['profile_sha256']==json.loads((HERE.parent/'kernel443/profile-export-validation.json').read_text())['profile_sha256']
def metrics(values):
 xs=sorted(v/1000 for v in values);assert xs
 return dict(median_ms=round(statistics.median(xs),3),p95_ms=round(xs[min(len(xs)-1,len(xs)*95//100)],3),maximum_ms=round(xs[-1],3))
def focus(text,queued,af=False):
 fs=[tuple(map(int,m)) for m in re.findall(r'FRAME_IPA_PREPARE epoch=1 sof=(\d+) combined=(\d+) focus-us=(\d+) dispatch-us=(\d+) focus-status=(-?\d+) tone-prepared=(\d+)',text)]
 ts=[tuple(map(int,m)) for m in re.findall(r'TONE_IPA_PREPARE epoch=1 sof=(\d+) cached=(\d+) dispatch-us=(\d+) status=(-?\d+)',text)]
 f={r[0]:r for r in fs};t={r[0]:r for r in ts};assert len(f)==len(fs) and len(t)==len(ts)
 prepare=re.findall(r'FOCUS_WORKSPACE_PREPARE epoch=1 width=(\d+) height=(\d+) bytes=(\d+)',text)
 assert len(prepare)==1 and int(prepare[0][2]) in [0,307200]
 assert re.findall(r'FOCUS_WORKSPACE_STOP epoch=1 bytes=(\d+)',text)==['0']
 assert queued<=set(t) and all(t[s][3]==0 for s in queued)
 if not f:
  assert prepare[0][2]=='0' and all(t[s][1]==0 for s in queued)
  return dict(lens_focus_active=False,workspace_bytes=0,stop_workspace_bytes=0)
 assert queued<=set(f) and prepare[0][2]=='307200'
 assert all(f[s][1]==1 and f[s][4]==0 and t[s][1]==f[s][5] for s in queued)
 deferred={s for s in queued if not f[s][5]}
 if not af:assert not deferred
 phases=[tuple(map(int,m)) for m in re.findall(r'FOCUS_TIMING epoch=1 sof=(\d+) sync-start-us=(\d+) map-us=(\d+) sample-us=(\d+) score-us=(\d+) unmap-us=(\d+) sync-end-us=(\d+)',text)]
 by_sof={r[0]:r[1:] for r in phases};assert len(by_sof)==len(phases) and queued<=set(by_sof)
 assert all(sum(by_sof[s])<=f[s][2] for s in queued)
 return dict(lens_focus_active=True,workspace_bytes=307200,stop_workspace_bytes=0,combined_calls=len(queued),deferred_for_lens_ack=len(deferred),focus_measurement=metrics([f[s][2] for s in queued]),focus_phases={n:metrics([by_sof[s][i] for s in queued]) for i,n in enumerate(['sync_start','map','sample','score','unmap','sync_end'])},sample_over33ms_sofs=sorted(s for s in queued if by_sof[s][2]>33000))
rows=[];completed=0;plugins=set()
assert set(state['captures'])=={'1280x720-isolated','1920x1080-isolated'}
for name,summary in state['captures'].items():
 text=(root/name/'client.log').read_text();w=summary['width'];h=summary['height']
 assert summary['mapped_candidate_core'] and summary['actual_sensor']==[4608,2592]
 samples=[tuple(map(int,m)) for m in re.findall(r'GST_IMAGE frame=(\d+) width=(\d+) height=(\d+) bytes=(\d+) pts=(\d+) hash=(\d+) sequence=(\d+) wall-ns=(\d+)',text)]
 assert len(samples)==120 and [s[0] for s in samples]==list(range(120))
 assert all(s[1:4]==(w,h,w*h*3//2) and s[5]>0 for s in samples)
 assert all(b[4]>a[4] and b[6]>a[6] and b[7]>a[7] for a,b in zip(samples,samples[1:]))
 app={int(p) for p in re.findall(r'APPLICATION_PROCESS pid=(\d+)',text)};ipa={int(p) for p in re.findall(r'IPA stats pid=(\d+)',text)}
 assert len(app)==len(ipa)==1 and not app&ipa
 row=gst.audit_gst(text,'s5kgw1',width=w,height=h,stride=w,coarse_bytes=summary['coarse_bytes'])
 assert row['queued_images']==summary['ipe_completed'];queued={int(s) for s in re.findall(r'IPE_TONE_QUEUE epoch=1 sof=(\d+)',text)}
 assert len(queued)==row['queued_images']
 row.update(capture=name,consumer='libcamerasrc/appsink',timestamp_fps=round(111e9/(samples[-1][4]-samples[8][4]),3),wall_fps=round(111e9/(samples[-1][7]-samples[8][7]),3),steady_missing_sofs=sum(b[6]-a[6]-1 for a,b in zip(samples[8:],samples[9:])),focus=focus(text,queued))
 rows.append(row);completed+=summary['ipe_completed'];plugins.add(summary['plugin_sha256'])
assert len(plugins)==1
other=[]
assert set(state['other_captures'])=={'imx319-scene-isolated','s5k3m5-scene-isolated','imx471-scene-isolated','s5kgw1-af-isolated'}
for name,summary in state['other_captures'].items():
 text,splits=join_split_frame_record((root/name/'client.log').read_text())
 row=auto.audit_auto(text,summary['model'],root/name)
 dispatch=re.findall(r'CAPTURE_DISPATCH queued=(\d+) callback-tid=(\d+) process-tid=(\d+) event-peak=(\d+)',text);assert len(dispatch)==1
 q,cb,process,peak=map(int,dispatch[0]);pid=int(re.search(r'ADAPT_PID value=(\d+)',text)[1]);assert q==1 and cb!=process==pid and 1<=peak<=4
 queued={int(s) for s in re.findall(r'IPE_TONE_QUEUE epoch=1 sof=(\d+)',text)};assert len(queued)==row['queued_images']==summary['ipe_completed']
 row.update(capture=name,model=summary['model'],sensor_size=summary['sensor_size'],application_dispatch_queued=True,split_records_rejoined=splits,focus=focus(text,queued,summary['af']))
 if summary['af']:
  assert summary['af_scanned'] and 'AF_POLICY_REQUEST phase=1 ' in text
  terminal=int(re.search(r'AF_TRIGGER_RESULT scanning=1 terminal=(\d+) focused=[01]',text)[1]);assert terminal in [2,3]
  commands=[];active=None;move_sofs=set();deferred_sofs=set()
  for line in text.splitlines():
   f=re.search(r'FRAME_IPA_PREPARE epoch=1 sof=(\d+) combined=1 .* focus-status=0 tone-prepared=(\d+)',line)
   if f:
    active=int(f[1])
    if f[2]=='0':deferred_sofs.add(active)
   c=re.search(r'Focus command serial=(\d+) position=(\d+) result=(-?\d+) at=(\d+)',line)
   if c:
    assert active in deferred_sofs and active not in move_sofs and c[3]=='0' and int(c[4])>0
    commands.append(tuple(map(int,c.groups())));move_sofs.add(active)
   t=re.search(r'TONE_IPA_PREPARE epoch=1 sof=(\d+) cached=0 .* status=0',line)
   if t and int(t[1]) in deferred_sofs:assert int(t[1]) in move_sofs
  assert commands and move_sofs==deferred_sofs
  assert [c[0] for c in commands]==list(range(1,len(commands)+1))
  assert all(b[3]>a[3] for a,b in zip(commands,commands[1:]))
  row.update(af_scanned=True,af_terminal=terminal,af_focused=summary['af_focused'],successful_host_lens_commands=len(commands),lens_command_precedes_fallback_tone=True,ack_call_order_from_unchanged_source_contract=True)
 other.append(row);completed+=summary['ipe_completed']
compatibility=[]
assert set(state['compatibility'])=={'raw','dual'}
for kind,summary in state['compatibility'].items():
 text=(root/('compatibility-'+kind)/'client.log').read_text();assert summary['passed'] and summary['frames']==6 and 'failed=0 result=0' in text
 pairs=re.findall(r'RawPair request=(\d+) pix-sof=(\d+) raw-sof=(\d+) pix-start=(\d+) raw-start=(\d+) delta-ns=(\d+) tolerance-ns=(\d+) matched=(\d+)',text)
 assert len(pairs)==6 and all(p[1]==p[2] and int(p[5])<=int(p[6]) and p[7]=='1' for p in pairs)
 images=re.findall(r'RAW_IMAGE request=(\d+) format=(\S+) sequence=(\d+) timestamp=(\d+) bytes=(\d+) status=(\d+) sample-hash=(\d+)',text)
 assert len(images)==(6 if kind=='raw' else 12) and all(int(i[3])>0 and int(i[4])>0 and i[5]=='0' and int(i[6])>0 for i in images)
 stop=re.findall(r'IPE_HISTORY_STOP epoch=1 prepared=(\d+) committed=(\d+) discarded=(\d+) superseded=(\d+) aborted=(\d+) pending=(\d+)',text);assert len(stop)==1
 prepared,committed,discarded,superseded,aborted,pending=map(int,stop[0]);assert not pending and not superseded and prepared==committed+discarded+aborted
 if kind=='raw':assert not summary['ipe_completed'] and not committed and all(t not in text for t in ['PD10_READY ','IPE_TONE_PREPARE ','IPE_TONE_QUEUE '])
 else:assert committed==6
 assert re.search(r'REQUEST_STOP_CANCEL .* raw=1',text) and re.search(r'FOCUS_WORKSPACE_STOP epoch=1 bytes=0',text)
 assert not any(x in text for x in ['IPE_TONE_REJECT','IFE_GTM_REJECT','IMAGE_PAIR_TIMEOUT'])
 compatibility.append(dict(kind=kind,**summary));completed+=summary['ipe_completed']
benchmarks=[]
assert len(state['focus_benchmarks'])==4
for name,b in state['focus_benchmarks'].items():
 assert b['fixture_passed'] and b['checksum_consistent'] and b['repetitions']==16 and b['alternating_old_new_order'] and b['cached_full_not_dma']
 benchmarks.append(dict(fixture=name,**b,speedup_ratio=round(b['reference_median_us']/b['optimized_median_us'],3)))
s=state['candidate_final_status'];assert s['jobs']==s['completed']==s['direct_completed']==completed
assert not any(s[k] for k in ['users','running','failed','cancelled','first_error','fatal','pinned','orphans'])
assert (root/'kernel-log-private.txt').read_text().count('A5 IPE frame completed request=')==completed
r=dict(stage=446,attempt=attempt,rows=rows,other_cameras_and_af=other,compatibility=compatibility,cached_phone_focus_benchmarks=benchmarks,total_ipe_completed=completed,same_sof_pd10_actual_gtm_wb_and_success_history=True,retained441_modules_and443_main_mode4_stock_profile=True,other_three_stock_profiles_unchanged=True,ipa_signature_proxy_byte_identical444=True,formal440_restored=True,new_kernel_faults=0,taint=0,installed=False,historical441_backlog_root_cause_closed=False,long_recording_accepted=False,absolute_optical_or_af_distance_calibration_accepted=False,full_goal_complete=False,passed=True)
(HERE/'hardware-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
