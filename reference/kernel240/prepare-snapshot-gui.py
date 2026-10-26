"""Derive a bounded CPU-rendered Snapshot diagnostic with camera-state cleanup."""
from pathlib import Path
import ast

R=Path(__file__).resolve().parent
s=(R/'native-megapixels-startup.py').read_text()
s=s.replace("assert (which,kind)==('rear','rgb')","assert (which,kind)==('front','rgb')")
s=s.replace('k240-megapixels-startup','k240-snapshot-cairo')
s=s.replace("trace=None;trace_removed=False;", "settings_before=None;settings_changed=False;gpu_abort=False;trace=None;trace_removed=False;")
s=s.replace("selected=['PATH','HOME','USER','LOGNAME','LANG','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','WAYLAND_DISPLAY','DISPLAY','XDG_DATA_DIRS','XDG_CONFIG_DIRS']",
 "selected=['PATH','HOME','USER','LOGNAME','LANG','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','WAYLAND_DISPLAY','DISPLAY','XDG_DATA_DIRS','XDG_CONFIG_DIRS']")
s=s.replace("if k in selected};env['PATH']='/usr/bin:/bin'", "if k in selected or k.startswith(('GDK_','GSK_','GTK_','MESA_'))};env['PATH']='/usr/sbin:/usr/bin:/sbin:/bin'")
s=s.replace("env['G_MESSAGES_DEBUG']='all'", """env.update(GSK_RENDERER='cairo',GDK_DISABLE='gl,vulkan,dmabuf,offload',GSK_DEBUG='renderer',
  RUST_LOG='snapshot=debug,aperture=debug',GST_DEBUG='pipewiresrc:6,basesink:6,gtk4paintablesink:5,camerabin:4',GST_DEBUG_NO_COLOR='1')""")
s=s.replace("assert (proc/'comm').read_text().strip()!='megapixels'", "assert (proc/'comm').read_text().strip() not in ['megapixels','snapshot']")
s=s.replace("args=['/usr/bin/megapixels']", """args=['/usr/bin/snapshot']
 settings_before=subprocess.check_output(['gsettings','get','org.gnome.Snapshot','last-camera-id'],env=env,preexec_fn=demote,timeout=5).decode().strip()
 (out/'gsettings-last-camera-before-private.txt').write_text(settings_before+'\\n')
 subprocess.run(['gsettings','set','org.gnome.Snapshot','last-camera-id','Built-in Front Camera'],env=env,preexec_fn=demote,check=True,timeout=5)
 settings_changed=True""")
s=s.replace('k240_gui_startup','k240_snapshot_cairo')
a=s.index(" event=trace/'events/i2c/i2c_write'")
b=s.index(" process=subprocess.Popen",a)
s=s[:a]+""" for name in ['vb2_v4l2_buf_done','vb2_v4l2_dqbuf']:
  event=trace/'events/v4l2'/name;assert 'field:int minor;' in (event/'format').read_text()
  (event/'filter').write_text('minor >= 0 && minor < 8');assert 'parse_error' not in (event/'filter').read_text()
  (event/'enable').write_text('1')
 (trace/'tracing_on').write_text('1');save('snapshot-cairo-preview-trace-armed')
"""+s[b:]
a=s.index(" try:stdout,stderr=process.communicate(timeout=12)")
b=s.index(" if stdout:",a)
s=s[:a]+""" deadline=time.monotonic()+16
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
"""+s[b:]
s=s.replace(" (out/'stdout-private.json').write_bytes(stdout);", """ if settings_changed:
  attempt('gsettings-restore',lambda:subprocess.run(['gsettings','set','org.gnome.Snapshot','last-camera-id',settings_before],env=env,preexec_fn=demote,check=True,timeout=5))
 (out/'stdout-private.json').write_bytes(stdout);""")
s=s.replace('i2c-control-trace-private.txt','video-buffer-trace-private.txt')
s=s.replace("application='megapixels'", "application='snapshot'")
s=s.replace('app_still_running_at12s=timed',"app_still_running_at16s=timed,gpu_fault_abort=gpu_abort,gtk_renderer='cairo',gdk_disabled='gl,vulkan,dmabuf,offload'")
s=s.replace('default_desktop_environment=True',"desktop_session_environment=True,only_this_app_uses_cpu_renderer=True,last_camera_setting_restored=not settings_changed or subprocess.check_output(['gsettings','get','org.gnome.Snapshot','last-camera-id'],env=env,preexec_fn=demote,timeout=5).decode().strip()==settings_before")
s=s.replace("completed=not error and process is not None", "completed=not error and not gpu_abort and process is not None")
ast.parse(s)
(R/'native-snapshot-cairo.py').write_text(s)

start=(R/'start-gui-repro.py').read_text()
start=start.replace('native-megapixels-startup.py','native-snapshot-cairo.py').replace('k240-megapixels-startup','k240-snapshot-cairo')
start=start.replace('megapixels-launch','snapshot-cairo-launch').replace("str(source),'rear','rgb'", "str(source),'front','rgb'")
start=start.replace("assert not (r/'k240-snapshot-cairo').exists()", "assert json.loads((r/'k240-snapshot-fault-stop/summary.json').read_text())['camera_devices_suspended'];assert not (r/'k240-snapshot-cairo').exists()")
start=start.replace('Megapixels startup diagnostic submitted once; S5K candidate source retained, not built or installed','Bounded Snapshot CPU-rendered diagnostic submitted once; observed default Vulkan faults retained')
start=start.replace('Poll this same GUI worker; inspect stderr/exit and cleanup. Prioritize actual camera app failure before S5K power work.','Poll this exact GUI worker; verify real new buffers, sink renders, no new faults and full camera-state cleanup. No shutter.')
ast.parse(start);(R/'start-snapshot-cairo.py').write_text(start)

poll=(R/'poll-gui-repro.py').read_text()
poll=poll.replace('k240-megapixels-startup','k240-snapshot-cairo').replace('megapixels-poll','snapshot-cairo-poll').replace('megapixels-gui-logs','snapshot-cairo-gui-logs').replace('megapixels-startup-validation','snapshot-cairo-startup-validation')
poll=poll.replace('Megapixels diagnostic terminal','Snapshot CPU-rendered diagnostic terminal').replace('Inspect actual GUI stderr/exit, then fix camera desktop integration; preserve S5K source-only candidate','Inspect actual frame/render evidence and fault deltas before any desktop launcher change')
poll=poll.replace('print(json.dumps(data))', "print(json.dumps({k:v for k,v in data.items() if k!='logs'}))")
ast.parse(poll);(R/'poll-snapshot-cairo.py').write_text(poll)
print('Snapshot CPU-rendered bounded GUI diagnostic prepared; no shutter; source parsed')
