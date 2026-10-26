"""Audit the completed cycles of r1 independently of its interrupted long case."""
from pathlib import Path
import ast,importlib.util,json,re
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;root=P/'runtime-collected-r1'
state=json.loads((root/'state.json').read_text());assert state['terminal'] and state['formal_modules_restored'] and state['services_restored'] and not state['new_faults'] and state['taint_after']==0
spec=importlib.util.spec_from_file_location('auto441',HERE.parent/'kernel441/frame-audit.py');audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
src=(HERE.parent/'kernel442/check-full.py').read_text();node=next(n for n in ast.parse(src).body if isinstance(n,ast.FunctionDef) and n.name=='join_split_frame_record');exec(ast.get_source_segment(src,node))
rows=[]
normalizer=importlib.util.spec_from_file_location('normal449',HERE/'normalize-probe-log.py');normal=importlib.util.module_from_spec(normalizer);normalizer.loader.exec_module(normal)
for name,summary in state['captures'].items():
 text,sample_splits=normal.join_split_sample_record((root/name/'client.log').read_text());text,splits=join_split_frame_record(text)
 identity=re.findall(r'APPLICATION_IDENTITY uid=(\d+) euid=(\d+) capeff=(\S+)',text);assert len(identity)==1 and identity[0][:2]==('10000','10000') and int(identity[0][2],16)==0
 assert len(re.findall(r'LIFECYCLE_MANAGER starts=1 ',text))==1
 assert len(set(re.findall(r'LIFECYCLE_CAMERA pointer=(\d+)',text)))==1
 starts=list(re.finditer(r'^LIFECYCLE_BEGIN cycle=(\d+) output=(\d+)x(\d+) previous-tid=(\d+) application-allowed=(\S+)$',text,re.M));assert len(starts)==3
 tids=set();total=0;queued=0;cycles=[]
 for i,start in enumerate(starts):
  assert int(start[1])==i;w,h=map(int,start.group(2,3));assert (w,h)==([(1280,720),(1920,1080),(1280,720)][i])
  end=re.search(r'^LIFECYCLE_END cycle='+str(i)+r' status=0$',text[start.start():],re.M);assert end
  part=text[start.start():start.start()+end.end()];epoch=i+1
  for line in part.splitlines():
   if any(marker in line for marker in ['IFE_GTM_QUEUE ','IFE_GTM_APPLIED ','PD10_READY ','IPE_OBSERVE ','IPE_TONE_PREPARE ','IPE_TONE_QUEUE ','IPE_RECEIPT ','AWB_STATE ']):
    actual=re.search(r'epoch=(\d+)',line)
    if actual:assert int(actual[1])==epoch
  row=audit.audit_auto(part,'s5kgw1',root/name/'captures'/f'cycle-{i}',width=w,height=h,stride=w,coarse_bytes=123648 if w==1280 else 261120)
  cap=re.findall(r'CAPACITY_START epoch='+str(epoch)+r' tid=(\d+) status=0 reason=selected active=1 users=1 original=(\S+) selected=(\S+)',part);assert len(cap)==1
  tid,original,selected=cap[0];tids.add(tid)
  assert re.search(r'CAPACITY_STOP epoch='+str(epoch)+' tid='+tid+r' status=0 reason=restored active=0 users=0 original='+re.escape(original)+' selected='+re.escape(selected),part)
  assert re.search(r'LIFECYCLE_AFTER_STOP tid='+tid+' allowed='+re.escape(original)+' application-allowed='+re.escape(original),part)
  if i:assert start[4]==tid
  samples=re.findall(r'SAMPLE sequence=(\d+) width=(\d+) height=(\d+) stride=(\d+) bytes=(\d+)',part);assert len(samples)==row['frames'] and all(tuple(map(int,s[1:]))==(w,h,w,w*h*3//2) for s in samples)
  app=set(re.findall(r'ADAPT_PID value=(\d+)',part));ipa=set(re.findall(r'IPA stats pid=(\d+)',part));assert len(app)==len(ipa)==1 and bool(app&ipa)==(not summary['isolated'])
  dispatch=re.findall(r'CAPTURE_DISPATCH queued=(\d+) callback-tid=(\d+) process-tid=(\d+) event-peak=(\d+)',part);assert len(dispatch)==1
  q,callback,process,peak=map(int,dispatch[0]);assert q==1 and str(callback)==tid and str(process) in app and callback!=process and 1<=peak<=4
  cycles.append(dict(cycle=i,epoch=epoch,width=w,height=h,**row,original_affinity_restored_while_manager_alive=True));total+=row['frames'];queued+=row['queued_images']
 assert len(tids)==1 and total==summary['frames'] and queued==summary['ipe_completed']
 rows.append(dict(capture=name,uid=10000,effective_capabilities=0,isolated=summary['isolated'],same_manager_camera_and_thread_across_three_cycles=True,cycles=cycles,frames=total,physical_ipe_completed=queued,split_application_records_rejoined=splits,split_sample_records_rejoined=sample_splits,passed=True))
long=(root/'user-sustained-1080/client.log').read_text();frames=[tuple(map(int,m)) for m in re.findall(r'GST_IMAGE frame=(\d+) .* pts=(\d+) hash=\d+ sequence=(\d+) wall-ns=(\d+)',long)]
assert frames and [r[0] for r in frames]==list(range(len(frames)))
assert 'FIXTURE_CHILD status=2 exited=0 exit=-1 signalled=1' in long and 'GST_RESULT ' not in long
fixture=(HERE.parent/'kernel363/pipeline-fixture.c').read_text();assert 'time(NULL)-start>50' in fixture and 'kill(-child,SIGINT)' in fixture
r=dict(stage=449,attempt='r1',completed_lifecycle_rows=rows,lifecycle_frames=sum(r['frames'] for r in rows),lifecycle_ipe_completed=sum(r['physical_ipe_completed'] for r in rows),long_case_interrupted_by_retained_fixture_50s_limit=True,long_case_last_consumed_frame=len(frames)-1,long_case_consumed_frames=len(frames),long_case_pts_span_seconds=round((frames[-1][1]-frames[0][1])/1e9,3),long_case_accepted=False,orphan_cleanup_and_final_restoration_required=True,production448_unchanged=True,full_goal_complete=False,passed=True)
(HERE/'lifecycle-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
