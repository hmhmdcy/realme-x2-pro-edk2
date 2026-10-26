"""Own only our isolated camera-only PipeWire and WirePlumber processes."""
from pathlib import Path
import json,os,shutil,signal,subprocess,sys,time
mode=int(sys.argv[1]);assert mode in [6000002,6000003,6000004,6000005,6000006,6000008]
root=Path('/var/lib/samurai/k263-user')/('isolated-'+str(mode));assert not root.exists();root.mkdir(mode=0o700)
for name in ['runtime','config','state']:(root/name).mkdir(mode=0o700)
tools=Path('/var/lib/samurai/k263-tools')
pwconf=root/'pipewire263.conf';wpconf=root/'wireplumber263.conf'
shutil.copyfile(tools/'pipewire263.conf',pwconf)
shutil.copyfile(tools/('wireplumber263-on.conf' if mode in [6000003,6000004,6000006] else 'wireplumber263-off.conf'),wpconf)
env=os.environ.copy()
env.update(PIPEWIRE_RUNTIME_DIR=str(root/'runtime'),PIPEWIRE_REMOTE='samurai263',XDG_CONFIG_HOME=str(root/'config'),XDG_STATE_HOME=str(root/'state'),GST_PLUGIN_PATH='/var/lib/samurai/k263-candidate',GST_REGISTRY=str(root/'gst-registry.bin'))
env.pop('SAMURAI_CAMERA_COPY',None)
if mode in [6000005,6000006,6000008]:env['SPA_PLUGIN_DIR']='/var/lib/samurai/k263-spa'
if mode in [6000005,6000006,6000008]:env['WIREPLUMBER_DEBUG']='4'
processes=[];logs=[];result=None;cleanup=[]
try:
 for name,args in [('pipewire',['pipewire','-c',str(pwconf)]),('wireplumber',['wireplumber','-c',str(wpconf),'-p','camera-test'])]:
  if name=='wireplumber':
   deadline=time.monotonic()+5
   while not (root/'runtime/samurai263').exists() and time.monotonic()<deadline:
    assert processes[0].poll() is None,'Isolated PipeWire exited';time.sleep(.05)
   assert (root/'runtime/samurai263').exists(),'Isolated socket absent'
  log=(root/(name+'-private.log')).open('xb');logs.append(log)
  p=subprocess.Popen(args,env=env,stdout=log,stderr=subprocess.STDOUT)
  processes.append(p)
  if name=='wireplumber':time.sleep(3)
 assert all(p.poll() is None for p in processes),'Isolated daemon exited'
 q=subprocess.run(['/usr/bin/python3',str(tools/'pipewire-probe.py'),'6000000'],env=env,capture_output=True,timeout=23)
 (root/'probe-stdout-private.json').write_bytes(q.stdout);(root/'probe-stderr-private.txt').write_bytes(q.stderr)
 result=json.loads(q.stdout);result['probe_exit_code']=q.returncode
 result['isolated_rule_requested']=mode in [6000003,6000004,6000006]
 if mode in [6000004,6000006,6000008]:assert result['remote_node_reliable']=='true','Node policy did not reach the server'
 if mode in [6000005,6000006,6000008]:
  mapped=Path('/proc',str(processes[1].pid),'maps').read_text()
  result['spa_candidate_mapped']='/var/lib/samurai/k263-spa/libcamera/libspa-libcamera.so' in mapped
  assert result['spa_candidate_mapped'],'Candidate SPA plugin was not loaded'
 assert q.returncode==0
finally:
 for p in reversed(processes):
  if p.poll() is None:p.terminate()
  try:p.wait(timeout=4)
  except subprocess.TimeoutExpired:p.kill();p.wait(timeout=2);cleanup.append('forced daemon kill')
 for log in logs:log.close()
 if result is not None:
  result['isolated_daemons_stopped']=all(p.poll() is not None for p in processes)
  result['isolated_cleanup_errors']=cleanup
  (root/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
if result is not None:print(json.dumps(result),flush=True)
assert not cleanup
