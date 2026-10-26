"""Prepare bounded GUI startup reproduction, preserving graph/controls/rails."""
from pathlib import Path
import ast
import json

R=Path(__file__).resolve().parent
source=(R/'native-upright-r2.py').read_text().replace('k240-upright-paired-r15-r2','k240-megapixels-startup')
old=" env=dict(PATH='/usr/bin:/bin',HOME=user.pw_dir,XDG_RUNTIME_DIR='/run/user/10000',LIBCAMERA_LOG_LEVELS='*:INFO,SimplePipeline:DEBUG,Debayer:DEBUG,IPASoftBL:DEBUG')"
assert source.count(old)==1
source=source.replace(old,""" desktop=[]
 for proc in Path('/proc').glob('[0-9]*'):
  try:
   if (proc/'comm').read_text().strip()=='phosh' and int((proc/'status').read_text().split('Uid:',1)[1].split()[0])==10000:desktop.append(proc)
  except OSError:pass
 assert len(desktop)==1
 inherited={k.decode():v.decode() for item in (desktop[0]/'environ').read_bytes().split(b'\\0') if b'=' in item for k,v in [item.split(b'=',1)]}
 selected=['PATH','HOME','USER','LOGNAME','LANG','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','WAYLAND_DISPLAY','DISPLAY','XDG_DATA_DIRS','XDG_CONFIG_DIRS']
 env={k:v for k,v in inherited.items() if k in selected};env['PATH']='/usr/bin:/bin';env['HOME']=user.pw_dir
 assert all(k in env for k in ['XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','WAYLAND_DISPLAY'])
 env['G_MESSAGES_DEBUG']='all'
 assert not any(k in env for k in ['LD_LIBRARY_PATH','LIBCAMERA_IPA_MODULE_PATH','LIBCAMERA_IPA_PROXY_PATH','LIBCAMERA_IPA_CONFIG_PATH'])
 for proc in Path('/proc').glob('[0-9]*'):
  try:assert (proc/'comm').read_text().strip()!='megapixels','Existing camera app; inspect it instead of duplicating'
  except FileNotFoundError:pass""")
source=source.replace(" args=['/run/samurai-camera240-probes/upright-paired-probe240',sensor,selected_id,model,entity,kind,str(dims[0]),str(dims[1]),'1']", " args=['/usr/bin/megapixels']")
source=source.replace(" set_controls(sensor,{'digital_gain':256,'vertical_blanking':2126})", " # Leave all sensor controls unchanged for the actual GUI startup.")
source=source.replace('k240_upright_controls','k240_gui_startup')
source=source.replace('process.communicate(timeout=65)','process.communicate(timeout=12)')
source=source.replace('import fcntl,hashlib,json,os,pwd,re,signal,struct,subprocess,sys,time,traceback','import fcntl,hashlib,json,os,pwd,re,resource,signal,struct,subprocess,sys,time,traceback')
source=source.replace('def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)',
 'def demote():resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)')
a=source.index(" frames=data.get('frames',[]) if data else []")
source=source[:a]+''' report=dict(stage=240,application='megapixels',app_exit_code=process.returncode if process else None,
  app_still_running_at12s=timed,forced_kill=killed,worker_exception=bool(error),
  all_formats_restored=bool(saved_formats) and after_formats==saved_formats,media_graph_restored=media_before is not None and media_after==media_before,
  sensor_controls_restored=bool(saved_controls) and control_match,rails_unchanged=saved_rails is not None and actual_rails==saved_rails,
  camera_devices_suspended=suspended,mclk1_mclk2_disabled=clock_off,restore_errors=restore_errors,
  fault_delta=faults,taint=int(Path('/proc/sys/kernel/tainted').read_text()),trace_instance_removed=trace_removed,
  no_shutter_action=True,no_scene_images_saved=True,default_desktop_environment=True,
  existing_idle_wireplumber_not_stopped=True)
 completed=not error and process is not None and not restore_errors and not any(faults.values()) and all(report[k] for k in ['all_formats_restored','media_graph_restored','sensor_controls_restored','rails_unchanged','camera_devices_suspended','mclk1_mclk2_disabled','trace_instance_removed'])
 report['diagnostic_completed']=completed;(out/'summary.json').write_text(json.dumps(report,indent=2)+'\\n')
 state.update(state='terminal',exit_code=0 if completed else 1);save('terminal');print(json.dumps(report),flush=True)
raise SystemExit(state['exit_code'])
'''
ast.parse(source);(R/'native-megapixels-startup.py').write_text(source)
print('Bounded Megapixels GUI startup reproduction prepared with complete camera-state cleanup')
