"""Exercise the installed default desktop camera path, without candidate overrides."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time
mode=int(sys.argv[1]);assert mode in list(range(6000090,6000095))+[6000101,6000111,6000121,6000131,6000132,6000133,6000141,6000142,6000143,6000151,6000152,6000153,6000154]
scenario=mode-80 if mode>=6000150 else (mode-70 if mode>=6000140 else (mode-60 if mode>=6000130 else (mode-30 if mode>=6000100 else mode-20)))
root=Path('/var/lib/samurai/k265-user')/('system-'+str(mode));assert not root.exists();root.mkdir(mode=0o700)
tools=Path('/var/lib/samurai/k265-compat-tools');env=os.environ.copy()
for key in ['PIPEWIRE_RUNTIME_DIR','PIPEWIRE_REMOTE','SPA_PLUGIN_DIR','LD_LIBRARY_PATH','LD_PRELOAD','GST_PLUGIN_PATH','SAMURAI_CAMERA_COPY']:env.pop(key,None)
env.update(GST_REGISTRY=str(root/'gst-registry.bin'),K264_SYSTEM_PLUGIN='0',GST_PLUGIN_PATH='/var/lib/samurai/k265-candidate',LD_LIBRARY_PATH='/var/lib/samurai/k265-candidate',PYTHONFAULTHANDLER='1')
if mode>=6000130:env.update(GST_PLUGIN_PATH='/var/lib/samurai/k265-candidate-v3',LD_LIBRARY_PATH='/var/lib/samurai/k265-candidate-v3',K265_CANDIDATE_V3='1')
if mode>=6000140:env.update(GST_PLUGIN_PATH='/var/lib/samurai/k265-candidate-v4',LD_LIBRARY_PATH='/var/lib/samurai/k265-candidate-v4',K265_CANDIDATE_V4='1')
if mode>=6000150:
 for k in ['GST_PLUGIN_PATH','LD_LIBRARY_PATH','K265_CANDIDATE_V3','K265_CANDIDATE_V4']:env.pop(k,None)
 env['K264_SYSTEM_PLUGIN']='1'
clients=[];logs=[];results=[];failure=None;forced=[]
def start(label,hold,duration,photo=False):
 child=env.copy();child.update(K264_HOLD_SECONDS=str(hold),K264_DURATION=str(duration))
 if photo:child['K264_PHOTO_PATH']=str(root/'front-shared-private.jpg')
 out=(root/(label+'-stdout-private.json')).open('xb');err=(root/(label+'-stderr-private.txt')).open('xb');logs.extend([out,err])
 p=subprocess.Popen(['/usr/bin/python3',str(tools/('system-photo-probe.py' if photo else 'compat-probe.py')),str(2000001 if photo else 6000000)],env=child,cwd=root,stdout=out,stderr=err);clients.append(p)
 return p,label,out,err
def finish(item):
 p,label,out,err=item;p.wait(timeout=32);out.flush();err.flush()
 (root/(label+'-exit-private.json')).write_text(json.dumps(dict(exit_code=p.returncode)))
 raw=(root/(label+'-stdout-private.json')).read_bytes()
 assert raw,'client '+label+' produced no JSON, exit='+str(p.returncode)
 r=json.loads(raw);r['label']=label;r['exit_code']=p.returncode;r['not_recycled_errors']=(root/(label+'-stderr-private.txt')).read_text(errors='replace').count('was not recycled');results.append(r);return r
def native():
 props=json.loads(subprocess.check_output(['/usr/bin/python3',str(tools/'select-front.py')],env=env,timeout=6));assert props['node.reliable']=='true' and props['node.reliable.broadcast']=='true'
 label='native';out=(root/(label+'-stdout-private.json')).open('xb');err=(root/(label+'-stderr-private.txt')).open('xb');logs.extend([out,err]);p=subprocess.Popen(['/var/lib/samurai/k264-tools/native-stream-probe',props['node.name']],env=env,stdout=out,stderr=err);clients.append(p);return p,label,out,err
try:
 if mode==6000154:
  r=finish(start('all-held',1.2,16));assert r['pts_span_seconds']>14 and r['buffers']>32
 elif mode in [6000121,6000131,6000141,6000151]:
  long=start('long',.35,52)
  for i in range(6):finish(start('short-'+str(i),.12,2))
  r=finish(long);assert r['pts_span_seconds']>45
 elif mode==6000111:
  long=start('long',.18,32)
  for i in range(3):finish(start('short-'+str(i),.12,4))
  r=finish(long);assert r['pts_span_seconds']>28
 elif scenario==6000070:
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
  else:assert r['held_pts_changed']==0 and r['application_copy_env'] is None and r['source_plugin']==('/usr/lib/gstreamer-1.0/libgstpipewire.so' if mode>=6000150 else env['GST_PLUGIN_PATH']+'/libgstpipewire.so') and r['remote_node_reliable']=='true'
except BaseException as e:failure=type(e).__name__+': '+str(e)
finally:
 for p in reversed(clients):
  if p.poll() is None:p.terminate()
  try:p.wait(timeout=4)
  except subprocess.TimeoutExpired:p.kill();p.wait(timeout=2);forced.append('forced client cleanup')
 for log in logs:log.close()
 report=dict(mode=mode,clients=results,failure=failure,client_exit_codes={str(p.pid):p.returncode for p in clients},forced_cleanup=forced,production_default_remote_used=True,application_copy_flag=False,candidate_library_overrides=mode<6000150)
 (root/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
assert failure is None and not forced
