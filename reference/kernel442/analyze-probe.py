"""Report bounded timing data; image and IQ data stay private."""
from pathlib import Path
import json,re,sys
import host
attempt=sys.argv[1] if len(sys.argv)>1 else 'r1';root=host.PRIVATE/('runtime-collected-'+attempt)
text=(root/'1280x720-isolated/client.log').read_text()
rows=[dict(zip(['sof','enter','store','end','copy','write'],map(int,m))) for m in re.findall(r'CAPTURE_IO sequence=(\d+) enter=(\d+) store=(\d+) end=(\d+) copy-mean-ns=(\d+) store-ns=(\d+)',text)]
assert rows and all(r['end']>=r['store']>=r['enter'] and r['copy']==r['store']-r['enter'] and r['write']==r['end']-r['store'] for r in rows)
def summary(key):
 xs=sorted(r[key]/1e6 for r in rows)
 return dict(median_ms=round(xs[len(xs)//2],3),p95_ms=round(xs[min(len(xs)-1,len(xs)*95//100)],3),maximum_ms=round(xs[-1],3))
dispatch=re.findall(r'CAPTURE_DISPATCH queued=(\d+) callback-tid=(\d+) process-tid=(\d+) event-peak=(\d+)',text)
queued=False;peak=0
if dispatch:
 assert len(dispatch)==1
 queued,callback,process,peak=map(int,dispatch[0]);app=int(re.findall(r'ADAPT_PID value=(\d+)',text)[0])
 assert (queued and process==app and callback!=process and 1<=peak<=4) or (not queued and process==callback and process!=app and peak==0)
state=json.loads((root/'state.json').read_text())
staged=json.loads((Path(__file__).resolve().parent/f'runtime-staging-{attempt}-validation.json').read_text())
baseline=json.loads((Path(__file__).resolve().parents[1]/'kernel441/build-validation.json').read_text())
baseline_core=next(r['sha256'] for r in baseline['runtime_files'] if r['name']=='libcamera.so.0.7.2')
out=dict(stage=442,attempt=attempt,frames_with_io_timing=len(rows),copy_and_luma=summary('copy'),file_write=summary('write'),callback_io_max_ms=round(max((r['copy']+r['write'])/1e6 for r in rows),3),blocking_callback_on_camera_worker=not bool(queued),app_event_queue_peak=peak,existing_cam_app_queues_processing_to_app_event_loop=True,pipeline_changed=staged['core_sha256']!=baseline_core,capture_succeeded=state['captures']['1280x720-isolated']['exit_code']==0,passed=True)
(Path(__file__).resolve().parent/f'callback-timing-{attempt}-validation.json').write_text(json.dumps(out,indent=2)+'\n')
(Path(__file__).resolve().parent/'callback-timing-validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
