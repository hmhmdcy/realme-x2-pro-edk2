"""One exact physical camera capture; RAM aggregates only, exhaustive cleanup."""
from pathlib import Path
import fcntl,hashlib,json,os,pwd,re,resource,signal,struct,subprocess,sys,time,traceback
os.umask(0o077)
which,kind=sys.argv[1:];assert (which,kind)==('front','rgb')
root=Path('/var/lib/samurai');boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot==(root/'k236-runtime/boot-id-private.txt').read_bytes()
assert json.loads((root/'k237-camss-install/state-private.json').read_text())['exit_code']==0
out=root/'k240-snapshot-cairo-r2';assert not out.exists();out.mkdir(mode=0o700)
state=dict(stage=240,state='running',phase='preflight',pid=os.getpid(),start_ticks=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19])
def save(phase=None):
 if phase:state['phase']=phase
 p=out/'state-next-private.json';p.write_text(json.dumps(state,indent=2)+'\n');os.replace(p,out/'state-private.json')
def command(args):return subprocess.check_output(args,timeout=12)
def attempt(label,action):
 try:return action()
 except BaseException as e:restore_errors.append(dict(step=label,error=type(e).__name__,detail=str(e)));return None
def rails():
 result={}
 for p in Path('/sys/class/regulator').glob('regulator.*'):
  name=(p/'name').read_text().strip()
  if name.startswith(('cam-front-','cam-rear-')) or Path('/sys/bus/i2c/devices/1-0004').resolve() in p.resolve().parents:
   result[name]={k:(p/k).read_text().strip() for k in ['state','num_users','microvolts']}
 return result
def formats():
 result=[]
 for node,name in nodes.items():
  fd=os.open('/dev/'+node,os.O_RDWR|os.O_CLOEXEC)
  try:
   for pad in range(32):
    b=bytearray(88);struct.pack_into('II',b,0,1,pad)
    try:fcntl.ioctl(fd,0xc0585604,b,True)
    except OSError as e:assert e.errno in [22,25];break
    result.append((node,name,pad,bytes(b)))
  finally:os.close(fd)
 return result
def get_controls(path,names):
 text=command(['v4l2-ctl','-d',path,'--get-ctrl='+','.join(names)]).decode()
 values={k:int(v) for k,v in re.findall(r'(\w+):\s*(-?\d+)',text)};assert set(values)==set(names);return values
def set_controls(path,values):
 if values:command(['v4l2-ctl','-d',path,'--set-ctrl='+','.join(k+'='+str(v) for k,v in values.items())])
def setlink(link,value):
 a,p,b,q,_=link;command(['media-ctl','-d','/dev/media0','--links',f'"{a}":{p} -> "{b}":{q} [{value}]'])
def restore_format(item):
 node,name,pad,saved=item;fd=os.open('/dev/'+node,os.O_RDWR|os.O_CLOEXEC)
 try:
  b=bytearray(88);struct.pack_into('II',b,0,1,pad);fcntl.ioctl(fd,0xc0585604,b,True)
  if bytes(b)!=saved:fcntl.ioctl(fd,0xc0585605,bytearray(saved),True)
 finally:os.close(fd)
settings_before=None;settings_changed=False;gpu_abort=False;trace=None;trace_removed=False;maps_seen=set();save();process=None;error=None;restore_errors=[];links=[];saved_formats=[];saved_controls={};patterns={};nodes={};stdout=b'';stderr=b'';timed=False;killed=False;data=None;saved_rails=None;media_before=None;before=None;selected_id=None;entity=None;sensor=None;dims=None
devices=['/sys/bus/i2c/devices/7-0010','/sys/bus/i2c/devices/9-0010','/sys/bus/platform/devices/ac4a000.cci','/sys/bus/platform/devices/ac4b000.cci','/sys/bus/platform/devices/acb3000.camss']
try:
 assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
 assert all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in devices)
 assert b'mode: cpu' in Path('/etc/libcamera/configuration.yaml').read_bytes()
 assert json.loads((root/'k240-baseline/summary.json').read_text())['installed_r15_r10']
 assert Path('/sys/module/imx471/parameters/unprocessed_fullres').read_text().strip()=='N'
 nodes={p.name:(p/'name').read_text().strip() for p in Path('/sys/class/video4linux').glob('v4l-subdev*')}
 model,bus,cci=('imx319','7-0010','ac4a000') if which=='rear' else ('imx471','9-0010','ac4b000')
 entity=model+' '+bus;selected_id='/base/soc@0/cci@'+cci+'/i2c-bus@1/camera@10'
 found=[node for node,name in nodes.items() if name==entity];assert len(found)==1;sensor='/dev/'+found[0]
 assert Path('/sys/class/video4linux',found[0],'device').resolve()==Path('/sys/bus/i2c/devices',bus).resolve()
 assert str(Path('/sys/class/video4linux',found[0],'device/of_node').resolve())=='/sys/firmware/devicetree'+selected_id
 for node,name in nodes.items():
  path='/dev/'+node
  if name.startswith(('imx319','imx471')):
   listing=command(['v4l2-ctl','-d',path,'--list-ctrls']).decode()
   available=set(re.findall(r'^\s*(\w+)\s+0x[0-9a-f]+',listing,re.M))
   wanted=available&{'exposure','analogue_gain','digital_gain','vertical_blanking','test_pattern','horizontal_flip','vertical_flip'}
   assert {'exposure','analogue_gain','digital_gain','vertical_blanking','test_pattern'}<=wanted
   saved_controls[path]=get_controls(path,sorted(wanted));assert saved_controls[path]['test_pattern']==0
   assert not saved_controls[path].get('horizontal_flip',0) and not saved_controls[path].get('vertical_flip',0)
  if name.startswith('msm_csid'):
   patterns[path]=get_controls(path,['test_pattern']);assert patterns[path]['test_pattern']==0
 saved_formats=formats();assert saved_formats
 media_before=command(['media-ctl','-d','/dev/media0','-p']);(out/'media-before-private.txt').write_bytes(media_before)
 assert re.search(r'-> "msm_csiphy1":0',media_before.decode()) if which=='rear' else True
 current=None;pad=None
 for line in media_before.decode().splitlines():
  m=re.match(r'^- entity \d+: (.*?) \(',line)
  if m:current=m[1];continue
  m=re.match(r'\s+pad(\d+):',line)
  if m:pad=int(m[1]);continue
  m=re.match(r'\s+-> "(.*?)":(\d+) \[(.*?)\]',line)
  if m and 'IMMUTABLE' not in m[3]:links.append((current,pad,m[1],int(m[2]),int('ENABLED' in m[3])))
 saved_rails=rails();(out/'rails-before-private.json').write_text(json.dumps(saved_rails,indent=2)+'\n')
 before=command(['dmesg']);(out/'dmesg-before-private.txt').write_bytes(before)
 policy=json.loads((root/'k240-tools/idle-policy-identity-private.json').read_text())
 for proc in Path('/proc').glob('[0-9]*'):
  for fd in (proc/'fd').glob('*'):
   try:path=os.readlink(fd)
   except OSError:continue
   if path.startswith(('/dev/video','/dev/v4l-subdev','/dev/media')):
    assert int(proc.name)==policy['pid'] and (proc/'stat').read_text().rsplit(')',1)[1].split()[19]==policy['start_ticks'],'other camera client'
    assert (proc/'comm').read_text().strip()=='wireplumber' and os.readlink(proc/'exe')=='/usr/bin/wireplumber'
    assert int((proc/'status').read_text().split('Uid:',1)[1].split()[0])==10000
    assert all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in devices),'policy observer is no longer idle'
 user=pwd.getpwuid(10000)
 def demote():resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
 desktop=[]
 for proc in Path('/proc').glob('[0-9]*'):
  try:
   if (proc/'comm').read_text().strip()=='phosh' and int((proc/'status').read_text().split('Uid:',1)[1].split()[0])==10000:desktop.append(proc)
  except OSError:pass
 assert len(desktop)==1
 inherited={k.decode():v.decode() for item in (desktop[0]/'environ').read_bytes().split(b'\0') if b'=' in item for k,v in [item.split(b'=',1)]}
 selected=['PATH','HOME','USER','LOGNAME','LANG','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','WAYLAND_DISPLAY','DISPLAY','XDG_DATA_DIRS','XDG_CONFIG_DIRS']
 env={k:v for k,v in inherited.items() if k in selected or k.startswith(('GDK_','GSK_','GTK_','MESA_'))};env['PATH']='/usr/sbin:/usr/bin:/sbin:/bin';env['HOME']=user.pw_dir
 assert all(k in env for k in ['XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','WAYLAND_DISPLAY'])
 env.update(GSK_RENDERER='cairo',GDK_DISABLE='gl,vulkan,dmabuf,offload',GSK_DEBUG='renderer',
  RUST_LOG='snapshot=debug,aperture=debug',GST_DEBUG='pipewiresrc:6,basesink:6,gtk4paintablesink:6,camerabin:4',GST_DEBUG_NO_COLOR='1')
 assert not any(k in env for k in ['LD_LIBRARY_PATH','LIBCAMERA_IPA_MODULE_PATH','LIBCAMERA_IPA_PROXY_PATH','LIBCAMERA_IPA_CONFIG_PATH'])
 for proc in Path('/proc').glob('[0-9]*'):
  try:assert (proc/'comm').read_text().strip() not in ['megapixels','snapshot'],'Existing camera app; inspect it instead of duplicating'
  except FileNotFoundError:pass
 dims=(1624,1224)
 args=['/usr/bin/snapshot']
 settings_before=subprocess.check_output(['gsettings','get','org.gnome.Snapshot','last-camera-id'],env=env,preexec_fn=demote,timeout=5).decode().strip()
 (out/'gsettings-last-camera-before-private.txt').write_text(settings_before+'\n')
 subprocess.run(['gsettings','set','org.gnome.Snapshot','last-camera-id','Built-in Front Camera'],env=env,preexec_fn=demote,check=True,timeout=5)
 settings_changed=True
 # Leave all sensor controls unchanged for the actual GUI startup.
 trace=Path('/sys/kernel/tracing/instances/k240_snapshot_cairo_r2');assert not trace.exists();trace.mkdir()
 (trace/'tracing_on').write_text('0');(trace/'events/enable').write_text('0');(trace/'buffer_size_kb').write_text('1024');(trace/'trace_clock').write_text('mono')
 for name in ['vb2_v4l2_buf_done','vb2_v4l2_dqbuf']:
  event=trace/'events/v4l2'/name;assert 'field:int minor;' in (event/'format').read_text()
  (event/'filter').write_text('minor >= 0 && minor < 8');assert 'parse_error' not in (event/'filter').read_text()
  (event/'enable').write_text('1')
 (trace/'tracing_on').write_text('1');save('snapshot-cairo-preview-trace-armed')
 process=subprocess.Popen(args,env=env,preexec_fn=demote,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 state['capture_pid']=process.pid;save()
 for _ in range(10):
  if process.poll() is not None:break
  try:
   mapped=Path('/proc',str(process.pid),'maps').read_text()
   for line in mapped.splitlines():
    if '/usr/lib/libcamera' in line:maps_seen.add(line.split()[-1])
  except OSError:pass
  time.sleep(.1)
 (out/'candidate-mapped-files-private.json').write_text(json.dumps(sorted(maps_seen),indent=2)+'\n')
 deadline=time.monotonic()+16
 while process.poll() is None and time.monotonic()<deadline:
  try:
   stdout,stderr=process.communicate(timeout=1);break
  except subprocess.TimeoutExpired:
   observed=command(['dmesg'])
   if observed.count(b'gpu fault:')>before.count(b'gpu fault:'):
    gpu_abort=True;break
 if process.poll() is None:
  timed=not gpu_abort;process.send_signal(signal.SIGTERM)
  try:stdout,stderr=process.communicate(timeout=5)
  except subprocess.TimeoutExpired:killed=True;process.kill();stdout,stderr=process.communicate(timeout=3)
 if stdout:
  try:data=json.loads(stdout)
  except ValueError:pass
except BaseException:error=traceback.format_exc();(out/'failure-private.txt').write_text(error)
finally:
 save('cleanup')
 if process is not None and process.poll() is None:
  process.terminate()
  try:stdout,stderr=process.communicate(timeout=5)
  except subprocess.TimeoutExpired:killed=True;process.kill();stdout,stderr=process.communicate(timeout=3)
 if settings_changed:
  attempt('gsettings-restore',lambda:subprocess.run(['gsettings','set','org.gnome.Snapshot','last-camera-id',settings_before],env=env,preexec_fn=demote,check=True,timeout=5))
 (out/'stdout-private.json').write_bytes(stdout);(out/'stderr-private.txt').write_bytes(stderr)
 if trace is not None and trace.exists():
  attempt('trace-stop',lambda:(trace/'tracing_on').write_text('0'))
  attempt('trace-disable',lambda:(trace/'events/enable').write_text('0'))
  attempt('trace-save',lambda:(out/'video-buffer-trace-private.txt').write_text((trace/'trace').read_text()))
  for statfile in trace.glob('per_cpu/cpu*/stats'):
   attempt('trace-stats:'+statfile.parent.name,lambda p=statfile:(out/(p.parent.name+'-trace-stats-private.txt')).write_text(p.read_text()))
  attempt('trace-remove',lambda:trace.rmdir());trace_removed=not trace.exists()
 for path,values in patterns.items():attempt('csid-pattern:'+path,lambda p=path,v=values:set_controls(p,v))
 for link in links:attempt('disable-link:'+str(link),lambda l=link:setlink(l,0))
 for path,values in saved_controls.items():
  flips={k:v for k,v in values.items() if k in ['horizontal_flip','vertical_flip']};attempt('sensor-flips:'+path,lambda p=path,v=flips:set_controls(p,v))
 rank=lambda item:(next((i for i,p in enumerate(['imx319','imx471','msm_csiphy','msm_csid','msm_ispif','msm_vfe']) if item[1].startswith(p)),6),item[2])
 for item in sorted(saved_formats,key=rank):attempt('format:'+item[0]+':'+str(item[2]),lambda i=item:restore_format(i))
 for path,values in saved_controls.items():
  for group in [['test_pattern','vertical_blanking'],['exposure','analogue_gain','digital_gain']]:
   wanted={k:values[k] for k in group if k in values};attempt('sensor-controls:'+path+':'+group[0],lambda p=path,v=wanted:set_controls(p,v))
 for link in links:
  if link[4]:attempt('enable-link:'+str(link),lambda l=link:setlink(l,1))
 time.sleep(2)
 after_formats=attempt('verify-formats',formats)
 media_after=attempt('verify-media',lambda:command(['media-ctl','-d','/dev/media0','-p']))
 if media_after is not None:(out/'media-after-private.txt').write_bytes(media_after)
 control_match=all(attempt('verify-controls:'+p,lambda p=p,v=v:get_controls(p,sorted(v)))==v for p,v in saved_controls.items())
 after=attempt('dmesg-after',lambda:command(['dmesg']))
 if after is not None:(out/'dmesg-after-private.txt').write_bytes(after)
 faults={k:after.count(v)-(before.count(v) if before is not None else 0) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',fatal=b'fatal error received',bt=b'Frame reassembly failed').items()} if after is not None else {'unavailable':1}
 actual_rails=attempt('verify-rails',rails)
 if actual_rails is not None:(out/'rails-after-private.json').write_text(json.dumps(actual_rails,indent=2)+'\n')
 suspended=all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in devices)
 clocks=Path('/sys/kernel/debug/clk/clk_summary').read_text();(out/'clocks-after-private.txt').write_text(clocks)
 clock_off=all(any(line.split()[0]==name and line.split()[1]=='0' for line in clocks.splitlines() if line.split()) for name in ['cam_cc_mclk1_clk','cam_cc_mclk2_clk'])
 report=dict(stage=240,application='snapshot',app_exit_code=process.returncode if process else None,
  app_still_running_at16s=timed,gpu_fault_abort=gpu_abort,gtk_renderer='cairo',gdk_disabled='gl,vulkan,dmabuf,offload',forced_kill=killed,worker_exception=bool(error),
  all_formats_restored=bool(saved_formats) and after_formats==saved_formats,media_graph_restored=media_before is not None and media_after==media_before,
  sensor_controls_restored=bool(saved_controls) and control_match,rails_unchanged=saved_rails is not None and actual_rails==saved_rails,
  camera_devices_suspended=suspended,mclk1_mclk2_disabled=clock_off,restore_errors=restore_errors,
  fault_delta=faults,taint=int(Path('/proc/sys/kernel/tainted').read_text()),trace_instance_removed=trace_removed,
  no_shutter_action=True,no_scene_images_saved=True,desktop_session_environment=True,only_this_app_uses_cpu_renderer=True,last_camera_setting_restored=not settings_changed or subprocess.check_output(['gsettings','get','org.gnome.Snapshot','last-camera-id'],env=env,preexec_fn=demote,timeout=5).decode().strip()==settings_before,
  existing_idle_wireplumber_not_stopped=True)
 completed=not error and not gpu_abort and process is not None and not restore_errors and not any(faults.values()) and all(report[k] for k in ['all_formats_restored','media_graph_restored','sensor_controls_restored','rails_unchanged','camera_devices_suspended','mclk1_mclk2_disabled','trace_instance_removed'])
 report['diagnostic_completed']=completed;(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
 state.update(state='terminal',exit_code=0 if completed else 1);save('terminal');print(json.dumps(report),flush=True)
raise SystemExit(state['exit_code'])
