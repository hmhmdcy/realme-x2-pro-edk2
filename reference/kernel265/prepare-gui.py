from pathlib import Path
import shlex
import host
R=Path(__file__).parent;B=R.parent/'kernel264'
s=(B/'native-snapshot-gui.py').read_text().replace('k264-services-current-private','k265-services-current-private').replace('k264-snapshot-gui','k265-snapshot-gui').replace('k264_snapshot_gui','k265_snapshot_gui').replace('stage=264','stage=265')
s=s.replace('settings_before=None;','controller=None;control_log=None;settings_before=None;',1)
needle=" state['capture_pid']=process.pid;save()";assert s.count(needle)==1
s=s.replace(needle,needle+"\n control_log=(out/'gui-auto-private.log').open('xb');controller=subprocess.Popen(['/usr/bin/python3','/var/lib/samurai/k265-tools/gui-auto.py'],stdin=subprocess.DEVNULL,stdout=control_log,stderr=subprocess.STDOUT)")
needle=" save('cleanup')";assert s.count(needle)==1
s=s.replace(needle,needle+"""
 if controller is not None:
  try:controller.wait(timeout=5)
  except subprocess.TimeoutExpired:controller.terminate();controller.wait(timeout=3)
 if control_log is not None:control_log.close()
""")
needle=" report['gui_control']=control";assert s.count(needle)==1
s=s.replace(needle,needle+"""
 report['controller_exit_code']=controller.returncode if controller else None
 completed=bool(completed and process.returncode==0 and controller is not None and controller.returncode==0 and control and control.get('accessible_shutter_action_accepted') and control.get('new_jpegs') and control.get('quit_action_sent'))
""")
p=R/'native-snapshot-gui.py';assert not p.exists();p.write_text(s)
data=(R/'gui-auto.py').read_bytes()
code="from pathlib import Path;import sys;p=Path('/var/lib/samurai/k265-tools/gui-auto.py');p.write_bytes(sys.stdin.buffer.read());p.chmod(0o644)"
host.ssh('python3 -c '+shlex.quote(code),input=data)
print('Prepared owned Snapshot preview/shutter/switch control')

