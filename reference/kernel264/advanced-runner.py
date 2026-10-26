"""Use private daemons to test unmodified shared-memory clients and reopen."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,time
mode=int(sys.argv[1]);assert mode in range(6000041,6000067)
scenario={6000041:6000017,6000042:6000018,6000043:6000014,6000044:6000019,6000045:6000016,6000046:6000015,6000047:6000017,6000048:6000018,6000049:6000014,6000050:6000019,6000051:6000016,6000052:6000015,6000053:'native-crash',6000054:'native-crash',6000055:6000018,6000056:'native-crash',6000057:'repeat-close',6000058:'repeat-crash',6000059:6000014,6000060:6000019,6000061:6000016,6000062:6000015,6000063:'long-hold-close',6000064:6000017,6000065:6000018,6000066:'native-crash'}[mode]
broadcast=True
root=Path('/var/lib/samurai/k264-user')/('isolated-'+str(mode));assert not root.exists();root.mkdir(mode=0o700)
for name in ['runtime','config','state']:(root/name).mkdir(mode=0o700)
tools=Path('/var/lib/samurai/k264-tools')
pwconf=root/'pipewire264.conf';wpconf=root/'wireplumber264.conf'
shutil.copyfile(tools/'pipewire264.conf',pwconf);shutil.copyfile(tools/'wireplumber264-off.conf',wpconf)
env=os.environ.copy();env.update(PIPEWIRE_RUNTIME_DIR=str(root/'runtime'),PIPEWIRE_REMOTE='samurai264',XDG_CONFIG_HOME=str(root/'config'),XDG_STATE_HOME=str(root/'state'),GST_PLUGIN_PATH='/var/lib/samurai/k264-candidate',GST_REGISTRY=str(root/'gst-registry.bin'),SPA_PLUGIN_DIR='/var/lib/samurai/k264-spa',WIREPLUMBER_DEBUG='4')
env.pop('SAMURAI_CAMERA_COPY',None)
if broadcast:
 env['LD_LIBRARY_PATH']='/var/lib/samurai/k264-core';env['K264_SYSTEM_PLUGIN']='1';env.pop('GST_PLUGIN_PATH',None)
processes=[];clients=[];logs=[];results=[];cleanup=[];failure=None
def start_client(label,hold,duration):
 child_env=env.copy();child_env.update(K264_HOLD_SECONDS=str(hold),K264_DURATION=str(duration))
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
   while not (root/'runtime/samurai264').exists() and time.monotonic()<deadline:
    assert processes[0].poll() is None;time.sleep(.05)
   assert (root/'runtime/samurai264').exists()
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
 elif scenario=='repeat-close':
  for i in range(3):
   short=start_client('short-'+str(i),.12,3);long=start_client('long-'+str(i),.18,9)
   finish_client(short);last=finish_client(long)
   assert last['pts_span_seconds']>7.5,'Remaining client stalled in close round '+str(i)
   time.sleep(.3);fd_counts.append(fd_count())
 elif scenario=='repeat-crash':
  for i in range(3):
   victim=start_client('victim-'+str(i),.35,20);survivor=start_client('survivor-'+str(i),.12,10)
   time.sleep(7);victim[0].kill();victim[0].wait(timeout=3)
   last=finish_client(survivor)
   assert last['pts_span_seconds']>8.5,'Remaining client stalled in crash round '+str(i)
   assert (root/('victim-'+str(i)+'-stderr-private.txt')).read_text().count('got new buffer')>5
   time.sleep(.3);fd_counts.append(fd_count())
 elif scenario=='long-hold-close':
  short=start_client('short-client',.12,6);long=start_client('long-client',1.2,16)
  finish_client(short);last=finish_client(long)
  assert last['pts_span_seconds']>14
 elif scenario=='native-crash':
  victim=start_client('crash-client',.35,25);native=start_native()
  time.sleep(7);victim[0].kill();victim[0].wait(timeout=3)
  finish_client(native)
 elif scenario==6000019:
  gst=start_client('gstreamer-peer',.18,12);native=start_native()
  finish_client(native);finish_client(gst)
 else:
  for i in range(4):
   finish_client(start_client('reopen-'+str(i),0 if i%2==0 else .12,6));time.sleep(.4);fd_counts.append(fd_count())
 mapped=Path('/proc',str(processes[1].pid),'maps').read_text();assert '/var/lib/samurai/k264-spa/libcamera/libspa-libcamera.so' in mapped
 if broadcast:
  for p in processes:assert '/var/lib/samurai/k264-core/libpipewire-0.3.so.0' in Path('/proc',str(p.pid),'maps').read_text()
 assert len(results)==(6 if scenario=='repeat-close' else 3 if scenario=='repeat-crash' else 2 if scenario=='long-hold-close' else 1 if scenario=='native-crash' else 2 if scenario in [6000010,6000014,6000017,6000019] else 1 if scenario in [6000011,6000015,6000018] else 4)
 for result in results:
  assert result['exit_code']==0
  if result['source_factory']=='pw_stream':assert result['errors_count']==0 and result['metadata_busy_missing']==0
  else:assert result['remote_node_reliable']=='true' and result['held_pts_changed']==0
  assert result['held_content_changed']==0 and result['not_recycled_errors']==0
  assert result['pts_strictly_increasing'] and result['shared_bufferpool']
 if scenario in [6000012,6000016,'repeat-close','repeat-crash']:assert len(set(fd_counts[1:]))==1,'FD count grew across reopen'
except BaseException as e:failure=type(e).__name__+': '+str(e)
finally:
 for p in reversed(processes+clients):
  if p.poll() is None:p.terminate()
  try:p.wait(timeout=4)
  except subprocess.TimeoutExpired:p.kill();p.wait(timeout=2);cleanup.append('forced process kill')
 for log in logs:log.close()
 report=dict(mode=mode,clients=results,fd_counts=fd_counts if 'fd_counts' in globals() else [],failure=failure,isolated_daemons_stopped=all(p.poll() is not None for p in processes),isolated_cleanup_errors=cleanup,spa_candidate_sha256=hashlib.sha256(Path('/var/lib/samurai/k264-spa/libcamera/libspa-libcamera.so').read_bytes()).hexdigest(),core_candidate_sha256=hashlib.sha256(Path('/var/lib/samurai/k264-core/libpipewire-0.3.so.0').read_bytes()).hexdigest() if broadcast else None,native_consumer_sha256=hashlib.sha256((tools/'native-stream-probe').read_bytes()).hexdigest() if any(r['source_factory']=='pw_stream' for r in results) else None,isolated_rule_requested=False,application_copy_flag=False)
 (root/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
assert failure is None and not cleanup
