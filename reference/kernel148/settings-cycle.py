"""Exercise existing Settings views on an isolated session; keep settings in RAM."""
from pathlib import Path
import json,os,subprocess,time
out=Path(os.environ['K148_IOCTL_LOG']).parent
env=dict(os.environ,GSETTINGS_BACKEND='memory',GSK_RENDERER='vulkan',XDG_CURRENT_DESKTOP='GNOME')
with (out/'settings-cycle-private.log').open('wb') as f:
    first=subprocess.Popen(['gnome-control-center','--gapplication-service'],env=env,stdout=f,stderr=subprocess.STDOUT)
    cleanup=dict(service_mode=True,quit_action_available=False,graceful_quit=False)
    try:
        time.sleep(1)
        for _ in range(2):
            for panel in ['system','display','multitasking','universal-access','keyboard','mouse','search','notifications','applications']:
                if first.poll() is not None:raise RuntimeError('Settings application exited during repaint')
                f.write(('PANEL '+panel+'\n').encode());f.flush()
                subprocess.run(['gnome-control-center',panel],env=env,stdout=f,stderr=subprocess.STDOUT,timeout=10,check=True)
                time.sleep(1.5)
    finally:
        if first.poll() is None:
            base=['gdbus','call','--session','--dest','org.gnome.Settings','--object-path','/org/gnome/Settings']
            try:
                query=subprocess.run(base+['--method','org.gtk.Actions.List'],env=env,capture_output=True,text=True,timeout=5)
                f.write(query.stdout.encode());f.write(query.stderr.encode());f.flush()
                cleanup['quit_action_available']=query.returncode==0 and "'quit'" in query.stdout
                if cleanup['quit_action_available']:
                    subprocess.run(base+['--method','org.gtk.Actions.Activate','quit','[]','{}'],env=env,stdout=f,stderr=subprocess.STDOUT,timeout=5,check=True)
                    cleanup['graceful_quit']=first.wait(timeout=5)==0
            except (subprocess.SubprocessError,FileNotFoundError):pass
            if first.poll() is None:
                first.terminate()
                try:first.wait(timeout=3)
                except subprocess.TimeoutExpired:first.kill();first.wait()
        cleanup['process_exit']=first.returncode
        (out/'settings-cleanup.json').write_text(json.dumps(cleanup,indent=2)+'\n')
print('SETTINGS_CYCLE_COMPLETED panels=18 memory_settings_backend=1 '+json.dumps(cleanup))
