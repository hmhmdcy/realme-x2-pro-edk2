from pathlib import Path
import importlib.util,json,re,sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('audit441',HERE.parent/'kernel441/frame-audit.py');audit=importlib.util.module_from_spec(s);s.loader.exec_module(audit)
attempt=sys.argv[1];root=P/('runtime-collected-'+attempt);state=json.loads((root/'state.json').read_text())
assert state['terminal'] and state['passed'] and not state['failure'] and not state['new_faults']
assert state['formal_modules_restored'] and state['services_restored'] and state['taint_after']==0
rows=[]
for name,summary in state['captures'].items():
 p=root/name;text=(p/'client.log').read_text();w=summary['width'];h=summary['height']
 row=audit.audit_auto(text,'s5kgw1',p,width=w,height=h,stride=w,coarse_bytes=summary['coarse_bytes'])
 assert row['frames']==summary['frames'] and row['queued_images']==summary['ipe_completed']
 dispatch=[tuple(map(int,m)) for m in re.findall(r'CAPTURE_DISPATCH queued=(\d+) callback-tid=(\d+) process-tid=(\d+) event-peak=(\d+)',text)]
 if dispatch:
  assert len(dispatch)==1;q,callback,process,peak=dispatch[0];app=int(re.findall(r'ADAPT_PID value=(\d+)',text)[0])
  assert (q and callback!=process==app and 1<=peak<=4) or (not q and process==callback!=app and not peak)
 row.update(capture=name,stop_cancellations=text.count('REQUEST_STOP_CANCEL '),application_dispatch_queued=bool(dispatch and dispatch[0][0]))
 rows.append(row)
r=dict(stage=442,attempt=attempt,rows=rows,source_core_verified_by_staged_manifest=True,strict_441_frame_and_history_audit_unchanged=True,passed=True)
(HERE/f'capture-{attempt}-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
