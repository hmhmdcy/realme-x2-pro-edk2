"""Run a test window on its own headless compositor without screen transitions."""
from pathlib import Path
import json,os,subprocess,sys,signal,shlex
out=Path(os.environ['K148_IOCTL_LOG']).parent
runtime=out/'runtime';runtime.mkdir(mode=0o700)
config=out/'headless-phoc.ini';config.write_text('[output:HEADLESS-1]\nscale = 1\n')
env=dict(os.environ,XDG_RUNTIME_DIR=str(runtime),WLR_BACKENDS='headless',WLR_HEADLESS_OUTPUTS='1',
         WLR_RENDERER='gles2',GSETTINGS_BACKEND='memory',XDG_CURRENT_DESKTOP='GNOME',
         WAYLAND_DISPLAY='k148-wayland',GSK_RENDERER='vulkan')
env.pop('DBUS_SESSION_BUS_ADDRESS',None);env.pop('DISPLAY',None)
kind=sys.argv[1];assert kind in ['cube','settings','settings-cycle']
app=shlex.join(['python3','/tmp/k148-session-app.py',kind,sys.argv[2]])
with (out/'headless-compositor-private.log').open('wb') as f:
    p=subprocess.Popen(['dbus-run-session','--','phoc','--no-xwayland','--config',str(config),
                        '--socket','k148-wayland','--exec',app],env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
    try:
        rc=p.wait(timeout=90 if kind in ['cube','settings-cycle'] else 15)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid,signal.SIGTERM)
        try:rc=p.wait(timeout=3)
        except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);rc=p.wait()
        if kind in ['cube','settings-cycle']:raise
        rc=0
    finally:
        if p.poll() is None:os.killpg(p.pid,signal.SIGTERM);p.wait(timeout=3)
receipt=out/'session-app-result.json'
if kind!='settings':
    assert receipt.exists(), 'Application did not record its completion'
    application=json.loads(receipt.read_text())
    assert application['exit']==0, 'Application failed independently of the compositor'
elif receipt.exists():assert json.loads(receipt.read_text())['exit']==0
print('HEADLESS_SESSION_EXIT='+str(rc),flush=True);raise SystemExit(rc)
