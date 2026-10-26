from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,os,pwd,subprocess
base=Path('/var/lib/samurai/k214-baseline');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(base/'boot-id-private.txt').read_bytes()
out=Path('/var/lib/samurai/k214-default-clients');listing=(out/'cam-list-stdout-private.txt').read_text();stderr=(out/'cam-list-stderr-private.txt').read_text()
user=pwd.getpwuid(10000)
def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
p=subprocess.run(['cam','--help'],preexec_fn=demote,env=dict(PATH='/usr/bin:/bin',HOME=user.pw_dir),capture_output=True,text=True,timeout=15)
(out/'cam-help-private.txt').write_text(p.stdout+p.stderr)
print(json.dumps(dict(camera_listing=listing,cam_help=p.stdout,cam_listing_errors=sum('ERROR' in line for line in stderr.splitlines()),gst_cli_tools_missing=not Path('/usr/bin/gst-inspect-1.0').exists(),app_plugin_exists=Path('/usr/lib/gstreamer-1.0/libgstapp.so').exists(),video_convert_plugin_exists=Path('/usr/lib/gstreamer-1.0/libgstvideoconvertscale.so').exists())))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=35);record=json.loads(p.stdout);(host.PRIVATE/'client-availability-context-private.json').write_bytes(p.stdout);print(json.dumps(record))
source=Path('/home/cy122/x2pro-linux/libcamera214-root/work/libcamera/src/libcamera-v0.7.2/src/gstreamer/gstlibcamerasrc.cpp').read_text().splitlines()
print(json.dumps(dict(source_property_lines=[line.strip() for line in source if 'camera-name' in line or 'num-buffers' in line or 'g_param_spec_' in line])))
