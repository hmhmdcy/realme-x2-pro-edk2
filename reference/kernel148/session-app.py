"""Record the application's exit separately from the headless compositor."""
from pathlib import Path
import json,os,subprocess,sys
out=Path(os.environ['K148_IOCTL_LOG']).parent
kind,value=sys.argv[1:3]
if os.environ.get('K148_PHONE_LAYOUT')=='1':
    assert Path(os.environ['XDG_RUNTIME_DIR']).is_relative_to(out)
    with (out/'headless-output-layout-private.txt').open('wb') as log:
        subprocess.run(['wlr-randr','--output','HEADLESS-1','--custom-mode','1080x2259@60Hz','--scale','3'],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=5)
        subprocess.run(['wlr-randr'],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=5)
if kind=='cube':
    frames=int(value);assert 1<=frames<=10000
    cmd=['/tmp/k148-sdk/usr/bin/vkcube','--wsi','wayland','--width','800','--height','600','--c',str(frames)]
elif kind=='settings':cmd=['/usr/bin/gnome-control-center',value]
elif kind=='settings-cycle':cmd=['python3','/tmp/k148-settings-cycle.py']
else:raise ValueError(kind)
rc=subprocess.run(cmd).returncode
(out/'session-app-result.json').write_text(json.dumps(dict(kind=kind,exit=rc),indent=2)+'\n')
print('SESSION_APP_EXIT='+str(rc),flush=True)
raise SystemExit(rc)
