"""Launch the real updated desktop entry; preserve normal libcamera ownership."""
from pathlib import Path
import re
R=Path(__file__).parent;s=(R/'native-system-natural.py').read_text()
s=s.replace('import fcntl,hashlib','import shlex,fcntl,hashlib')
s=re.sub(r"which,kind='front','rgb';delay=int\(sys.argv\[1\]\);assert delay in [^\n]+", "which,kind='front','rgb';delay=6000090",s,count=1)
s=s.replace("out=root/('k264-pipewire-'+str(delay)+'-r2')", "out=root/'k264-snapshot-gui'")
needle=" args=['/usr/bin/python3','/var/lib/samurai/k264-tools/system-runner.py',str(delay)]";assert s.count(needle)==1
s=s.replace(needle,""" launcher=Path(user.pw_dir)/'.local/share/applications/org.gnome.Snapshot.desktop'
 launch_text=launcher.read_text();args=shlex.split(next(line[5:] for line in launch_text.splitlines() if line.startswith('Exec=')))
 assert not any('SAMURAI_CAMERA_COPY' in x for x in args) and args[-1]=='/usr/bin/snapshot'
 assert 'GSK_RENDERER=cairo' in args and 'GDK_DISABLE=gl,vulkan,offload' in args
 assert subprocess.check_output(['gdbus','call','--session','--dest','org.gnome.ScreenSaver','--object-path','/org/gnome/ScreenSaver','--method','org.gnome.ScreenSaver.GetActive'],env=env,preexec_fn=demote,timeout=5).strip()==b'(false,)'
 picture_dir=subprocess.check_output(['/usr/bin/python3','-c',\"from gi.repository import GLib;print(GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_PICTURES) or '')\"],env=env,preexec_fn=demote,timeout=5).decode().strip()
 picture_root=Path(picture_dir) if picture_dir else Path(user.pw_dir)/'Pictures'
 assert picture_root.is_absolute() and Path(user.pw_dir) in picture_root.parents
 pictures_before={str(p) for p in picture_root.rglob('*') if p.is_file() and p.suffix.lower() in ['.jpg','.jpeg']}
 (out/'pictures-before-private.json').write_text(json.dumps(dict(root=str(picture_root),files=sorted(pictures_before)),indent=2)+'\\n')
 state['launcher_sha256']=hashlib.sha256(launcher.read_bytes()).hexdigest();save()""")
s=s.replace(" # Headless probe does not alter last-camera-id.", " subprocess.run(['gsettings','set','org.gnome.Snapshot','last-camera-id','Built-in Front Camera'],env=env,preexec_fn=demote,check=True,timeout=5)\n settings_changed=True")
s=s.replace('k264_pipewire','k264_snapshot_gui')
s=s.replace("application='camerabin-system-photo' if delay==6000084 else 'camera-clients',probe_result=data", "application='snapshot',launcher_sha256=state.get('launcher_sha256')")
s=s.replace('gui_window_used=False','gui_window_used=True')
s=s.replace('no_shutter_action=delay!=6000084,no_scene_images_saved=delay!=6000084', "no_shutter_action=not (out/'shutter-request-private.json').exists(),scene_capture_request_recorded=(out/'shutter-request-private.json').exists()")
s=s.replace('completed=data is not None and process.returncode==0 and not error and', "completed=process is not None and process.returncode in [0,-15] and not error and")
needle=" report['diagnostic_completed']=completed;";assert s.count(needle)==1
s=s.replace(needle,""" control=json.loads((out/'gui-control-summary-private.json').read_text()) if (out/'gui-control-summary-private.json').exists() else None
 report['gui_control']=control
 report['app_copy_environment_absent']=True
 report['diagnostic_completed']=completed;""")
(R/'native-snapshot-gui.py').write_text(s)
