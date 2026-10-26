"""Exercise the installed default desktop camera path, without candidate overrides."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time
mode=int(sys.argv[1]);assert mode in list(range(6000070,6000075))+list(range(6000080,6000085))
scenario=mode-10 if mode>=6000080 else mode
root=Path('/var/lib/samurai/k264-user')/('system-'+str(mode));assert not root.exists();root.mkdir(mode=0o700)
tools=Path('/var/lib/samurai/k264-tools');env=os.environ.copy()
for key in ['PIPEWIRE_RUNTIME_DIR','PIPEWIRE_REMOTE','SPA_PLUGIN_DIR','LD_LIBRARY_PATH','LD_PRELOAD','GST_PLUGIN_PATH','SAMURAI_CAMERA_COPY']:env.pop(key,None)
env.update(GST_REGISTRY=str(root/'gst-registry.bin'),K264_SYSTEM_PLUGIN='1')
clients=[];logs=[];results=[];failure=None;forced=[]
def start(label,hold,duration,photo=False):
 child=env.copy();child.update(K264_HOLD_SECONDS=str(hold),K264_DURATION=str(duration))
 if photo:child['K264_PHOTO_PATH']=str(root/'front-shared-private.jpg')
 out=(root/(label+'-stdout-private.json')).open('xb');err=(root/(label+'-stderr-private.txt')).open('xb');logs.extend([out,err])
 p=subprocess.Popen(['/usr/bin/python3',str(tools/('system-photo-probe.py' if photo else 'advanced-probe.py')),str(2000001 if photo else 6000000)],env=child,stdout=out,stderr=err);clients.append(p)
 return p,label,out,err
def finish(item):
 p,label,out,err=item;p.wait(timeout=32);out.flush();err.flush();r=json.loads((root/(label+'-stdout-private.json')).read_bytes());r['label']=label;r['exit_code']=p.returncode;r['not_recycled_errors']=(root/(label+'-stderr-private.txt')).read_text(errors='replace').count('was not recycled');results.append(r);return r
def native():
 props=json.loads(subprocess.check_output(['/usr/bin/python3',str(tools/'select-front.py')],env=env,timeout=6));assert props['node.reliable']=='true' and props['node.reliable.broadcast']=='true'
 label='native';out=(root/(label+'-stdout-private.json')).open('xb');err=(root/(label+'-stderr-private.txt')).open('xb');logs.extend([out,err]);p=subprocess.Popen([str(tools/'native-stream-probe'),props['node.name']],env=env,stdout=out,stderr=err);clients.append(p);return p,label,out,err
try:
 if scenario==6000070:
  r=finish(start('shared-hold',.12,20));assert r['pts_span_seconds']>18
 elif scenario==6000071:
  short=start('short',.12,6);long=start('long',.18,16);finish(short);r=finish(long);assert r['pts_span_seconds']>14
 elif scenario==6000072:
  victim=start('victim',.35,25);survivor=start('survivor',.12,18);time.sleep(9);victim[0].kill();victim[0].wait(timeout=3);r=finish(survivor);assert r['pts_span_seconds']>16
  assert (root/'victim-stderr-private.txt').read_text().count('got new buffer')>5
 elif scenario==6000073:
  gst=start('gstreamer',.18,12);c=native();finish(c);finish(gst)
 else:
  r=finish(start('photo',.12,12,photo=True));assert r['shutter_triggered'] and r['image_done_message'] and r['saved_jpeg_bytes']>1024
 for r in results:
  assert r['exit_code']==0 and r['held_content_changed']==0 and r['not_recycled_errors']==0 and r['pts_strictly_increasing'] and r['shared_bufferpool']
  if r['source_factory']=='pw_stream':assert r['zero_header_pts']==0 and r['errors_count']==0 and r['pts_span_seconds']>10
  else:assert r['held_pts_changed']==0 and r['application_copy_env'] is None and r['source_plugin']=='/usr/lib/gstreamer-1.0/libgstpipewire.so' and r['remote_node_reliable']=='true'
except BaseException as e:failure=type(e).__name__+': '+str(e)
finally:
 for p in reversed(clients):
  if p.poll() is None:p.terminate()
  try:p.wait(timeout=4)
  except subprocess.TimeoutExpired:p.kill();p.wait(timeout=2);forced.append('forced client cleanup')
 for log in logs:log.close()
 report=dict(mode=mode,clients=results,failure=failure,forced_cleanup=forced,production_default_remote_used=True,application_copy_flag=False,candidate_library_overrides=False)
 (root/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
assert failure is None and not forced
