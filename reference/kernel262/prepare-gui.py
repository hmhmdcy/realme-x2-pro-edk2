"""Derive the tested cleanup harness for the actual Snapshot launch command."""
from pathlib import Path
import hashlib,json,re
R=Path(__file__).parent
s=(R/'native-pipewire-probe.py').read_text()
s,count=re.subn(r"which,kind='front','rgb';delay=int\(sys.argv\[1\]\);assert delay in \[[^\n]+\]", "which,kind='front','rgb';delay=5000000",s,count=1)
assert count==1
s=s.replace("out=root/('k262-pipewire-'+str(delay)+'-r2')", "out=root/'k262-snapshot-gui'")
s=s.replace('import fcntl,hashlib','import shlex,fcntl,hashlib')
s=s.replace(" args=['/usr/bin/python3','/var/lib/samurai/k262-tools/pipewire-probe.py',str(delay)]", " launcher=Path(user.pw_dir)/'.local/share/applications/org.gnome.Snapshot.desktop'\n launch_text=launcher.read_text();args=shlex.split(next(line[5:] for line in launch_text.splitlines() if line.startswith('Exec=')))\n assert 'SAMURAI_CAMERA_COPY=1' in args and args[-1]=='/usr/bin/snapshot'\n assert subprocess.check_output(['gdbus','call','--session','--dest','org.gnome.ScreenSaver','--object-path','/org/gnome/ScreenSaver','--method','org.gnome.ScreenSaver.GetActive'],env=env,preexec_fn=demote,timeout=5).strip()==b'(false,)'\n state['launcher_sha256']=hashlib.sha256(launcher.read_bytes()).hexdigest();save()")
s=s.replace(" # Headless probe does not alter last-camera-id.", " subprocess.run(['gsettings','set','org.gnome.Snapshot','last-camera-id','Built-in Front Camera'],env=env,preexec_fn=demote,check=True,timeout=5)\n settings_changed=True")
s=s.replace('k262_pipewire','k262_snapshot_gui')
s=s.replace('time.monotonic()+(42 if delay==4000000 else 23)','time.monotonic()+35')
s=s.replace("application='pipewire-probe',probe_result=data", "application='snapshot',launcher_sha256=state.get('launcher_sha256')")
s=s.replace('gui_window_used=False','gui_window_used=True')
s=s.replace('no_shutter_action=delay not in [2000000,2000001,3000002],no_scene_images_saved=delay not in [2000000,2000001,3000002]', "no_shutter_action=not (out/'shutter-request-private.json').exists(),scene_capture_request_recorded=(out/'shutter-request-private.json').exists()")
s=s.replace('completed=data is not None and process.returncode==0 and not error and', 'completed=process is not None and process.returncode in [0,-15] and not error and')
compile(s,'native-snapshot-gui.py','exec')
(R/'native-snapshot-gui.py').write_text(s)
print(json.dumps(dict(source_sha256=hashlib.sha256(s.encode()).hexdigest(),actual_user_desktop_exec_used=True)))
