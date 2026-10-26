"""Observe one ordinary Snapshot launch with persistent kernel and app logs."""
from pathlib import Path
import importlib.util,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel269')
spec=importlib.util.spec_from_file_location('h',R/'host.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
code=r'''
from pathlib import Path
import hashlib,json,os,pwd,re,shlex,signal,subprocess,time,traceback
os.umask(0o077);out=Path('/var/lib/samurai/k269-snapshot-startup-r1');out.mkdir(mode=0o700)
state=dict(state='preflight',terminal=False);process=None;logger=None;trace=None
def save():(out/'state-private.json').write_text(json.dumps(state,indent=2)+'\n')
def processes():
 result=[]
 for p in Path('/proc').glob('[0-9]*'):
  try:result.append((p,(p/'comm').read_text().strip()))
  except OSError:pass
 return result
def faults(data):
 return {k:data.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',modem=b'crash detected in modem',fatal=b'fatal error received',gpu=b'gpu fault:').items()}
save();before=subprocess.check_output(['dmesg']);(out/'dmesg-before-private.log').write_bytes(before)
try:
 assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0' and not any(faults(before).values())
 assert not any(n in ['snapshot','megapixels'] for p,n in processes())
 assert all(Path('/sys/bus/i2c/devices',n,'power/runtime_status').read_text().strip()=='suspended' for n in ['7-0010','9-0010'])
 desktop=next(p for p,n in processes() if n=='phosh');assert b'--unlocked' in (desktop/'cmdline').read_bytes()
 u=pwd.getpwuid(10000)
 inherited={k.decode():v.decode() for x in (desktop/'environ').read_bytes().split(b'\0') if b'=' in x for k,v in [x.split(b'=',1)]}
 keys=['PATH','HOME','USER','LOGNAME','LANG','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','WAYLAND_DISPLAY','DISPLAY','XDG_DATA_DIRS','XDG_CONFIG_DIRS']
 env={k:v for k,v in inherited.items() if k in keys or k.startswith(('GDK_','GSK_','GTK_','MESA_'))}
 env['HOME']=u.pw_dir;env['PATH']='/usr/sbin:/usr/bin:/sbin:/bin'
 assert not any(k in env for k in ['LD_LIBRARY_PATH','SAMURAI_CAMERA_COPY','LIBCAMERA_IPA_MODULE_PATH'])
 launcher=Path(u.pw_dir)/'.local/share/applications/org.gnome.Snapshot.desktop'
 args=shlex.split(next(l[5:] for l in launcher.read_text().splitlines() if l.startswith('Exec=')))
 assert args==['/usr/bin/env','GSK_RENDERER=cairo','GDK_DISABLE=gl,vulkan,offload','/usr/bin/snapshot']
 def demote():os.initgroups(u.pw_name,u.pw_gid);os.setgid(u.pw_gid);os.setuid(u.pw_uid)
 logfd=os.open(out/'kernel-follow-private.log',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_SYNC,0o600)
 logger=subprocess.Popen(['dmesg','--follow','--raw'],stdout=logfd,stderr=subprocess.STDOUT);os.close(logfd)
 state.update(kernel_logger_pid=logger.pid,kernel_logger_start_ticks=Path('/proc',str(logger.pid),'stat').read_text().rsplit(')',1)[1].split()[19]);save()
 trace=Path('/sys/kernel/tracing/instances/k269_snapshot_startup_r1');trace.mkdir()
 (trace/'tracing_on').write_text('0');(trace/'events/enable').write_text('0');(trace/'buffer_size_kb').write_text('1024');(trace/'trace_clock').write_text('mono')
 for name in ['vb2_v4l2_buf_done','vb2_v4l2_dqbuf']:
  event=trace/'events/v4l2'/name;assert 'field:int minor;' in (event/'format').read_text();(event/'filter').write_text('minor >= 0 && minor < 8');(event/'enable').write_text('1')
 (trace/'tracing_on').write_text('1')
 log=(out/'snapshot-private.log').open('xb',buffering=0)
 process=subprocess.Popen(args,env=env,preexec_fn=demote,stdout=log,stderr=subprocess.STDOUT,cwd=u.pw_dir)
 state.update(state='observing-ordinary-launch',capture_pid=process.pid,capture_start_ticks=Path('/proc',str(process.pid),'stat').read_text().rsplit(')',1)[1].split()[19],launcher_sha256=hashlib.sha256(launcher.read_bytes()).hexdigest());save()
 start=time.monotonic();observations=[]
 for i in range(35):
  time.sleep(1)
  row=dict(seconds=round(time.monotonic()-start,2),app_exit=process.poll(),
    sensors={n:Path('/sys/bus/i2c/devices',n,'power/runtime_status').read_text().strip() for n in ['7-0010','9-0010']},
    memory={l.split(':',1)[0]:l.split(':',1)[1].strip() for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith(('MemAvailable:','SwapFree:'))})
  observations.append(row);(out/'observations-private.json').write_text(json.dumps(observations,indent=2)+'\n')
  delta={k:v-faults(before)[k] for k,v in faults(subprocess.check_output(['dmesg'])).items()}
  if process.poll() is not None or any(delta.values()):break
 state.update(state='closing-observed-application',duration_seconds=round(time.monotonic()-start,2));save()
 if process.poll() is None:
  process.terminate()
  try:process.wait(timeout=12)
  except subprocess.TimeoutExpired:
   state.update(state='application-did-not-exit',terminal=True);save();raise RuntimeError('Application did not exit; inspect before any further camera experiment')
 time.sleep(3)
 (trace/'tracing_on').write_text('0');raw=(trace/'trace').read_text();(out/'trace-private.txt').write_text(raw)
 after=subprocess.check_output(['dmesg']);(out/'dmesg-after-private.log').write_bytes(after)
 delta={k:v-faults(before)[k] for k,v in faults(after).items()}
 report=dict(stage=269,launch='existing-user-Snapshot-desktop-Exec',launcher_sha256=state['launcher_sha256'],
  duration_seconds=state['duration_seconds'],natural_early_exit=any(r['app_exit'] is not None for r in observations),app_exit_after_close=process.returncode,
  sensor_active_samples={n:sum(r['sensors'][n]=='active' for r in observations) for n in ['7-0010','9-0010']},
  capture_done_events=raw.count('vb2_v4l2_buf_done:'),capture_dequeue_events=raw.count('vb2_v4l2_dqbuf:'),fault_delta=delta,
  final_sensor_runtime={n:Path('/sys/bus/i2c/devices',n,'power/runtime_status').read_text().strip() for n in ['7-0010','9-0010']},
  taint=int(Path('/proc/sys/kernel/tainted').read_text()),camera_settings_unchanged=True,
  no_capture_or_desktop_source_patch=True,only_existing_cairo_launcher_workaround=True,
  previous_unexpected_reboot_not_yet_explained_or_fixed=True)
 (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');state.update(state='terminal',terminal=True,exit_code=0);save();print(json.dumps(report))
except BaseException:
 (out/'failure-private.txt').write_text(traceback.format_exc());state.update(state='failed',terminal=True,exit_code=1);save();raise
finally:
 if trace is not None and trace.exists():
  (trace/'tracing_on').write_text('0');(trace/'events/enable').write_text('0')
 if logger is not None and logger.poll() is None:logger.terminate();logger.wait(timeout=5)
'''
q=h.ssh('python3 -',input=code.encode(),timeout=80);(P/'snapshot-startup-private.json').write_bytes(q.stdout);d=json.loads(q.stdout)
(R/'snapshot-startup-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
