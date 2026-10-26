"""Use private daemons to test unmodified shared-memory clients and reopen."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,time
mode=int(sys.argv[1]);assert mode in [6000010,6000011,6000012,6000014,6000015,6000016,6000017,6000018,6000019,6000020,6000022,6000023,6000024,6000025,6000026,6000027,6000028,6000029,6000030,6000031,6000032,6000033] + list(range(6000034,6000040))
scenario={6000020:6000019,6000022:6000018,6000023:6000015,6000024:6000014,6000025:6000016,6000026:6000019,6000027:6000017,6000028:6000018,6000029:6000015,6000030:6000014,6000031:6000016,6000032:6000019,6000033:6000017}.get(mode,mode)
scenario={6000034:6000018,6000035:6000017,6000036:6000019,6000037:6000014,6000038:6000016,6000039:6000015}.get(mode,scenario)
broadcast=mode not in [6000010,6000011,6000012]
root=Path('/var/lib/samurai/k263-user')/('isolated-'+str(mode));assert not root.exists();root.mkdir(mode=0o700)
for name in ['runtime','config','state']:(root/name).mkdir(mode=0o700)
tools=Path('/var/lib/samurai/k263-tools')
pwconf=root/'pipewire263.conf';wpconf=root/'wireplumber263.conf'
shutil.copyfile(tools/'pipewire263.conf',pwconf);shutil.copyfile(tools/'wireplumber263-off.conf',wpconf)
env=os.environ.copy();env.update(PIPEWIRE_RUNTIME_DIR=str(root/'runtime'),PIPEWIRE_REMOTE='samurai263',XDG_CONFIG_HOME=str(root/'config'),XDG_STATE_HOME=str(root/'state'),GST_PLUGIN_PATH='/var/lib/samurai/k263-candidate',GST_REGISTRY=str(root/'gst-registry.bin'),SPA_PLUGIN_DIR='/var/lib/samurai/k263-spa',WIREPLUMBER_DEBUG='4')
env.pop('SAMURAI_CAMERA_COPY',None)
if broadcast:
 env['LD_LIBRARY_PATH']='/var/lib/samurai/k263-core';env['K263_SYSTEM_PLUGIN']='1';env.pop('GST_PLUGIN_PATH',None)
processes=[];clients=[];logs=[];results=[];cleanup=[];failure=None
def start_client(label,hold,duration):
 child_env=env.copy();child_env.update(K263_HOLD_SECONDS=str(hold),K263_DURATION=str(duration))
 out=(root/(label+'-stdout-private.json')).open('xb');err=(root/(label+'-stderr-private.txt')).open('xb');logs.extend([out,err])
 p=subprocess.Popen(['/usr/bin/python3',str(tools/'advanced-probe.py'),'6000000'],env=child_env,stdout=out,stderr=err);clients.append(p)
 return p,label,out,err
def finish_client(item):
 p,label,out,err=item;p.wait(timeout=28);out.flush();err.flush()
 result=json.loads((root/(label+'-stdout-private.json')).read_bytes());result['exit_code']=p.returncode;result['label']=label
 result['not_recycled_errors']=(root/(label+'-stderr-private.txt')).read_text(errors='replace').count('was not recycled')
 results.append(result)
 return result
def fd_count():return len(list(Path('/proc',str(processes[1].pid),'fd').iterdir()))
def start_native():
 props=json.loads(subprocess.check_output(['/usr/bin/python3',str(tools/'select-front.py')],env=env,timeout=6))
 assert str(props['node.reliable']).lower()=='true' and str(props['node.reliable.broadcast']).lower()=='true'
 label='native-pw_stream';out=(root/(label+'-stdout-private.json')).open('xb');err=(root/(label+'-stderr-private.txt')).open('xb');logs.extend([out,err])
 p=subprocess.Popen([str(tools/'native-stream-probe'),props['node.name']],env=env,stdout=out,stderr=err);clients.append(p)
 return p,label,out,err
try:
 for name,args in [('pipewire',['pipewire','-c',str(pwconf)]),('wireplumber',['wireplumber','-c',str(wpconf),'-p','camera-test'])]:
  if name=='wireplumber':
   deadline=time.monotonic()+5
   while not (root/'runtime/samurai263').exists() and time.monotonic()<deadline:
    assert processes[0].poll() is None;time.sleep(.05)
   assert (root/'runtime/samurai263').exists()
  log=(root/(name+'-private.log')).open('xb');logs.append(log);processes.append(subprocess.Popen(args,env=env,stdout=log,stderr=subprocess.STDOUT))
  if name=='wireplumber':time.sleep(3)
 assert all(p.poll() is None for p in processes)
 fd_counts=[fd_count()]
 if scenario in [6000010,6000014]:
  pair=[start_client('client-a',.12,12),start_client('client-b',.18,12)]
  for item in pair:finish_client(item)
 elif scenario in [6000011,6000015]:finish_client(start_client('all-held',1.2,16))
 elif scenario==6000017:
  short=start_client('short-client',.12,6);long=start_client('long-client',.18,16)
  finish_client(short);finish_client(long)
  assert results[1]['pts_span_seconds']>14,'Remaining client did not continue after peer closed'
 elif scenario==6000018:
  victim=start_client('crash-client',.35,25);survivor=start_client('survivor',.12,18)
  time.sleep(9);victim[0].kill();victim[0].wait(timeout=3)
  finish_client(survivor)
  assert results[0]['pts_span_seconds']>16,'Remaining client stalled after peer crash'
 elif scenario==6000019:
  gst=start_client('gstreamer-peer',.18,12);native=start_native()
  finish_client(native);finish_client(gst)
 else:
  for i in range(4):
   finish_client(start_client('reopen-'+str(i),0 if i%2==0 else .12,6));time.sleep(.4);fd_counts.append(fd_count())
 mapped=Path('/proc',str(processes[1].pid),'maps').read_text();assert '/var/lib/samurai/k263-spa/libcamera/libspa-libcamera.so' in mapped
 if broadcast:
  for p in processes:assert '/var/lib/samurai/k263-core/libpipewire-0.3.so.0' in Path('/proc',str(p.pid),'maps').read_text()
 assert len(results)==(2 if scenario in [6000010,6000014,6000017,6000019] else 1 if scenario in [6000011,6000015,6000018] else 4)
 for result in results:
  assert result['exit_code']==0
  if result['source_factory']=='pw_stream':assert result['errors_count']==0 and result['metadata_busy_missing']==0
  else:assert result['remote_node_reliable']=='true'
  assert result['held_content_changed']==0 and result['not_recycled_errors']==0
  assert result['pts_strictly_increasing'] and result['shared_bufferpool']
 if scenario in [6000012,6000016]:assert len(set(fd_counts[1:]))==1,'FD count grew across reopen'
except BaseException as e:failure=type(e).__name__+': '+str(e)
finally:
 for p in reversed(processes+clients):
  if p.poll() is None:p.terminate()
  try:p.wait(timeout=4)
  except subprocess.TimeoutExpired:p.kill();p.wait(timeout=2);cleanup.append('forced process kill')
 for log in logs:log.close()
 report=dict(mode=mode,clients=results,fd_counts=fd_counts if 'fd_counts' in globals() else [],failure=failure,isolated_daemons_stopped=all(p.poll() is not None for p in processes),isolated_cleanup_errors=cleanup,spa_candidate_sha256=hashlib.sha256(Path('/var/lib/samurai/k263-spa/libcamera/libspa-libcamera.so').read_bytes()).hexdigest(),core_candidate_sha256=hashlib.sha256(Path('/var/lib/samurai/k263-core/libpipewire-0.3.so.0').read_bytes()).hexdigest() if broadcast else None,isolated_rule_requested=False,application_copy_flag=False)
 (root/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
assert failure is None and not cleanup
