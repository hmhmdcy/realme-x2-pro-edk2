"""Bounded camera buffer and JPEG probe with state restoration."""
from pathlib import Path
import shlex,fcntl,hashlib,json,os,pwd,re,resource,signal,struct,subprocess,sys,time,traceback
os.umask(0o077)
which,kind='front','rgb';delay=6000090
root=Path('/var/lib/samurai');boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot==(root/'k269-work/boot-id-private.txt').read_bytes()
assert json.loads((root/'k237-camss-install/state-private.json').read_text())['exit_code']==0
system_services=[dict(name=p['comm'],pid=p['pid'],start_ticks=p['start_ticks']) for p in json.loads((root/'k269-services-current-private.json').read_text())['processes'] if p['comm'] in ['pipewire','wireplumber']]
def verify_system_services():
 for item in system_services:
  proc=Path('/proc',str(item['pid']))
  assert (proc/'stat').read_text().rsplit(')',1)[1].split()[19]==item['start_ticks']
  maps=(proc/'maps').read_text().splitlines()
  assert any(l.split()[-1]=='/usr/lib/libpipewire-0.3.so.0.1609.0' for l in maps)
  assert not any('/var/lib/samurai/k264-' in l and '.so' in l for l in maps)
  if item['name']=='wireplumber':assert any(l.split()[-1]=='/usr/lib/spa-0.2/libcamera/libspa-libcamera.so' for l in maps)
verify_system_services()

out=root/'k270-snapshot-gui-r1';assert not out.exists();out.mkdir(mode=0o700)
state=dict(stage=270,state='running',phase='preflight',pid=os.getpid(),start_ticks=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19])
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
controller=None;control_log=None;settings_before=None;settings_changed=False;gpu_abort=False;gpu_fds_seen=set();trace=None;trace_removed=False;maps_seen=set();save();process=None;error=None;restore_errors=[];links=[];saved_formats=[];saved_controls={};patterns={};nodes={};stdout=b'';stderr=b'';timed=False;killed=False;data=None;saved_rails=None;media_before=None;before=None;selected_id=None;entity=None;sensor=None;dims=None
devices=['/sys/bus/i2c/devices/7-0010','/sys/bus/i2c/devices/9-0010','/sys/bus/platform/devices/ac4a000.cci','/sys/bus/platform/devices/ac4b000.cci','/sys/bus/platform/devices/acb3000.camss']
try:
 assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
 assert all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in devices)
 assert b'mode: cpu' in Path('/etc/libcamera/configuration.yaml').read_bytes()
 command(['apk','info','--exists','libcamera=99990.7.2-r19'])
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
 observers=[p for p in Path('/proc').glob('[0-9]*') if (p/'comm').exists() and (p/'comm').read_text().strip()=='wireplumber'];assert len(observers)==1;policy=dict(pid=int(observers[0].name),start_ticks=(observers[0]/'stat').read_text().rsplit(')',1)[1].split()[19])
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
 env.update(PIPEWIRE_DEBUG='3',GSK_RENDERER='cairo',GDK_DISABLE='gl,vulkan,offload',GSK_DEBUG='renderer',GDK_DEBUG='dmabuf',
  RUST_LOG='snapshot=debug,aperture=debug',GST_DEBUG='pipewiresrc:6,basesink:6,gtk4paintablesink:6,camerabin:4',GST_DEBUG_NO_COLOR='1')
 assert not any(k in env for k in ['LD_LIBRARY_PATH','LIBCAMERA_IPA_MODULE_PATH','LIBCAMERA_IPA_PROXY_PATH','LIBCAMERA_IPA_CONFIG_PATH'])
 for proc in Path('/proc').glob('[0-9]*'):
  try:assert (proc/'comm').read_text().strip() not in ['megapixels','snapshot'],'Existing camera app; inspect it instead of duplicating'
  except FileNotFoundError:pass
 dims=(1624,1224)
 if delay in [3000000,3000001,3000002,6000000]:env.update(GST_PLUGIN_PATH='/var/lib/samurai/k264-candidate',GST_REGISTRY='/var/lib/samurai/k264-user/candidate-registry.bin')
 if delay in [3000001,3000002,4000000]:env['SAMURAI_CAMERA_COPY']='1'
 launcher=Path(user.pw_dir)/'.local/share/applications/org.gnome.Snapshot.desktop'
 launch_text=launcher.read_text();args=shlex.split(next(line[5:] for line in launch_text.splitlines() if line.startswith('Exec=')))
 assert not any('SAMURAI_CAMERA_COPY' in x for x in args) and args[-1]=='/usr/bin/snapshot'
 assert 'GSK_RENDERER=cairo' in args and 'GDK_DISABLE=gl,vulkan,offload' in args
 assert subprocess.check_output(['gdbus','call','--session','--dest','org.gnome.ScreenSaver','--object-path','/org/gnome/ScreenSaver','--method','org.gnome.ScreenSaver.GetActive'],env=env,preexec_fn=demote,timeout=5).strip()==b'(false,)'
 picture_dir=subprocess.check_output(['/usr/bin/python3','-c',"from gi.repository import GLib;print(GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_PICTURES) or '')"],env=env,preexec_fn=demote,timeout=5).decode().strip()
 picture_root=Path(picture_dir) if picture_dir else Path(user.pw_dir)/'Pictures'
 assert picture_root.is_absolute() and Path(user.pw_dir) in picture_root.parents
 pictures_before={str(p) for p in picture_root.rglob('*') if p.is_file() and p.suffix.lower() in ['.jpg','.jpeg']}
 (out/'pictures-before-private.json').write_text(json.dumps(dict(root=str(picture_root),files=sorted(pictures_before)),indent=2)+'\n')
 state['launcher_sha256']=hashlib.sha256(launcher.read_bytes()).hexdigest();save()
 settings_before=subprocess.check_output(['gsettings','get','org.gnome.Snapshot','last-camera-id'],env=env,preexec_fn=demote,timeout=5).decode().strip()
 (out/'gsettings-last-camera-before-private.txt').write_text(settings_before+'\n')
 subprocess.run(['gsettings','set','org.gnome.Snapshot','last-camera-id','Built-in Front Camera'],env=env,preexec_fn=demote,check=True,timeout=5)
 settings_changed=True
 # Leave all sensor controls unchanged for the actual GUI startup.
 trace=Path('/sys/kernel/tracing/instances/k270_snapshot_gui_r1');assert not trace.exists();trace.mkdir()
 (trace/'tracing_on').write_text('0');(trace/'events/enable').write_text('0');(trace/'buffer_size_kb').write_text('1024');(trace/'trace_clock').write_text('mono')
 for name in ['vb2_v4l2_buf_done','vb2_v4l2_dqbuf']:
  event=trace/'events/v4l2'/name;assert 'field:int minor;' in (event/'format').read_text()
  (event/'filter').write_text('minor >= 0 && minor < 8');assert 'parse_error' not in (event/'filter').read_text()
  (event/'enable').write_text('1')
 (trace/'tracing_on').write_text('1');save('snapshot-cairo-preview-trace-armed')
 process=subprocess.Popen(args,env=env,preexec_fn=demote,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 state['capture_pid']=process.pid;save()
 control_log=(out/'gui-auto-private.log').open('xb');controller=subprocess.Popen(['/usr/bin/python3','/var/lib/samurai/k270-tools/gui-auto-r1.py'],stdin=subprocess.DEVNULL,stdout=control_log,stderr=subprocess.STDOUT)
 for _ in range(10):
  if process.poll() is not None:break
  try:
   mapped=Path('/proc',str(process.pid),'maps').read_text()
   for line in mapped.splitlines():
    if '/usr/lib/libcamera' in line:maps_seen.add(line.split()[-1])
  except OSError:pass
  time.sleep(.1)
 (out/'candidate-mapped-files-private.json').write_text(json.dumps(sorted(maps_seen),indent=2)+'\n')
 deadline=time.monotonic()+95
 while process.poll() is None and time.monotonic()<deadline:
  try:
   stdout,stderr=process.communicate(timeout=1);break
  except subprocess.TimeoutExpired:
   for fd in Path('/proc',str(process.pid),'fd').glob('*'):
    try:target=os.readlink(fd)
    except OSError:continue
    if target.startswith('/dev/dri/'):gpu_fds_seen.add(target)
   observed=command(['dmesg'])
   if observed.count(b'gpu fault:')>before.count(b'gpu fault:'):
    gpu_abort=True;break
 if process.poll() is None:
  timed=not gpu_abort;process.send_signal(signal.SIGTERM)
  try:stdout,stderr=process.communicate(timeout=5)
  except subprocess.TimeoutExpired:killed=True;process.kill();stdout,stderr=process.communicate(timeout=3)
 if process.poll() is not None:stdout,stderr=process.communicate()
 if stdout:
  try:data=json.loads(stdout)
  except ValueError:pass
except BaseException:error=traceback.format_exc();(out/'failure-private.txt').write_text(error)
finally:
 save('cleanup')
 if controller is not None:
  try:controller.wait(timeout=5)
  except subprocess.TimeoutExpired:controller.terminate();controller.wait(timeout=3)
 if control_log is not None:control_log.close()

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
 # Production libcamera owns graph/formats/AE state. Observe its normal release.
 time.sleep(2)
 after_formats=attempt('verify-formats',formats)
 media_after=attempt('verify-media',lambda:command(['media-ctl','-d','/dev/media0','-p']))
 if media_after is not None:(out/'media-after-private.txt').write_bytes(media_after)
 control_match=all(attempt('verify-controls:'+p,lambda p=p,v=v:get_controls(p,sorted(v)))==v for p,v in saved_controls.items())
 patterns_and_flips_zero=all(get_controls(p,['test_pattern'])['test_pattern']==0 for p in set(patterns)|set(saved_controls)) and all(not get_controls(p,[name])[name] for p,values in saved_controls.items() for name in ['horizontal_flip','vertical_flip'] if name in values)
 after=attempt('dmesg-after',lambda:command(['dmesg']))
 if after is not None:(out/'dmesg-after-private.txt').write_bytes(after)
 faults={k:after.count(v)-(before.count(v) if before is not None else 0) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',fatal=b'fatal error received',bt=b'Frame reassembly failed').items()} if after is not None else {'unavailable':1}
 actual_rails=attempt('verify-rails',rails)
 if actual_rails is not None:(out/'rails-after-private.json').write_text(json.dumps(actual_rails,indent=2)+'\n')
 suspended=all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in devices)
 clocks=Path('/sys/kernel/debug/clk/clk_summary').read_text();(out/'clocks-after-private.txt').write_text(clocks)
 clock_off=all(any(line.split()[0]==name and line.split()[1]=='0' for line in clocks.splitlines() if line.split()) for name in ['cam_cc_mclk1_clk','cam_cc_mclk2_clk'])
 report=dict(stage=270,application='snapshot',launcher_sha256=state.get('launcher_sha256'),app_exit_code=process.returncode if process else None,
  outer_timeout_reached=timed,gpu_fault_abort=gpu_abort,gtk_renderer_requested='cairo',gui_window_used=True,application_gpu_device_fds=sorted(gpu_fds_seen),gdk_disabled='gl,vulkan,offload',forced_kill=killed,worker_exception=bool(error),
  formats_match_before=bool(saved_formats) and after_formats==saved_formats,media_graph_matches_before=media_before is not None and media_after==media_before,
  sensor_controls_match_before=bool(saved_controls) and control_match,rails_unchanged=saved_rails is not None and actual_rails==saved_rails,
  cleanup_policy='normal_libcamera_release_without_external_media_writes',test_patterns_and_flips_zero=patterns_and_flips_zero,
  camera_devices_suspended=suspended,mclk1_mclk2_disabled=clock_off,restore_errors=restore_errors,
  fault_delta=faults,taint=int(Path('/proc/sys/kernel/tainted').read_text()),trace_instance_removed=trace_removed,
  no_shutter_action=not (out/'shutter-request-private.json').exists(),scene_capture_request_recorded=(out/'shutter-request-private.json').exists(),desktop_session_environment=True,last_camera_setting_restored=not settings_changed or subprocess.check_output(['gsettings','get','org.gnome.Snapshot','last-camera-id'],env=env,preexec_fn=demote,timeout=5).decode().strip()==settings_before,
  existing_idle_wireplumber_not_stopped=True)
 completed=process is not None and process.returncode in [0,-15] and not error and not gpu_abort and process is not None and not restore_errors and not any(faults.values()) and all(report[k] for k in ['test_patterns_and_flips_zero','rails_unchanged','camera_devices_suspended','mclk1_mclk2_disabled','trace_instance_removed'])
 verify_system_services()
 report['production_service_identities_and_system_maps_verified']=True
 control=json.loads((out/'gui-control-summary-private.json').read_text()) if (out/'gui-control-summary-private.json').exists() else None
 report['gui_control']=control
 report['controller_exit_code']=controller.returncode if controller else None
 completed=bool(completed and process.returncode==0 and controller is not None and controller.returncode==0 and control and control.get('accessible_shutter_action_accepted') and control.get('new_jpegs') and control.get('quit_action_sent'))

 report['app_copy_environment_absent']=True
 report['diagnostic_completed']=completed;(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
 state.update(state='terminal',exit_code=0 if completed else 1);save('terminal');print(json.dumps(report),flush=True)
raise SystemExit(state['exit_code'])
