from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,os,pwd,subprocess
os.umask(0o077);base=Path('/var/lib/samurai/k214-baseline');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(base/'boot-id-private.txt').read_bytes()
out=Path('/var/lib/samurai/k214-default-clients');out.mkdir(mode=0o700)
sessions=[]
for p in Path('/proc').iterdir():
    if not p.name.isdigit():continue
    try:
        if (p/'comm').read_text().strip()=='phosh' and int((p/'status').read_text().split('Uid:',1)[1].split()[0])==10000:sessions.append(p)
    except OSError:pass
assert len(sessions)==1
saved=dict(item.split(b'=',1) for item in (sessions[0]/'environ').read_bytes().split(b'\0') if b'=' in item);user=pwd.getpwuid(10000)
registry=Path(saved[b'XDG_RUNTIME_DIR'].decode())/'samurai-camera214-registry.bin';assert not registry.exists()
env=dict(PATH='/usr/bin:/bin',HOME=user.pw_dir,XDG_RUNTIME_DIR=saved[b'XDG_RUNTIME_DIR'].decode(),GST_REGISTRY=str(registry),LIBCAMERA_LOG_LEVELS='*:INFO')
def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
results={}
for tag,argv in [('cam-list',['cam','-l']),('gst-camera',['gst-inspect-1.0','libcamerasrc']),('gst-identity',['gst-inspect-1.0','identity'])]:
    p=subprocess.run(argv,env=env,preexec_fn=demote,capture_output=True,text=True,timeout=30);(out/(tag+'-stdout-private.txt')).write_text(p.stdout);(out/(tag+'-stderr-private.txt')).write_text(p.stderr);results[tag]=dict(exit=p.returncode,stdout=p.stdout,stderr=p.stderr)
(out/'client-environment-private.json').write_text(json.dumps(env,indent=2)+'\n')
report=dict(stage=214,default_cam_list_exit=results['cam-list']['exit'],default_gstreamer_camera_plugin_exit=results['gst-camera']['exit'],gstreamer_camera_name_property_present='camera-name' in results['gst-camera']['stdout'],gstreamer_rgb_caps_present='RGB' in results['gst-camera']['stdout'],identity_eos_after_available='eos-after' in results['gst-identity']['stdout'],camera_listing=results['cam-list']['stdout'],plugin_loaded_from_installed_path='/usr/lib/gstreamer-1.0/libgstlibcamera.so' in results['gst-camera']['stdout'],capture_not_started=True)
(out/'inspection-summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=100);(host.PRIVATE/'default-client-inspection-host-private.log').write_bytes(p.stdout+p.stderr)
record=json.loads(p.stdout);(host.PRIVATE/'default-client-inspection-private.json').write_bytes(p.stdout);public={k:v for k,v in record.items() if k!='camera_listing'};(here/'default-client-inspection-validation.json').write_text(json.dumps(public,indent=2)+'\n');print(json.dumps(record))
