"""Read GTK version and CPU mmap-supported formats without starting a camera."""
from pathlib import Path
import json
import host
R=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,os,pwd,subprocess
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
assert json.loads((r/'k240-snapshot-cairo-r2/state-private.json').read_text())['state']=='terminal'
u=pwd.getpwuid(10000)
def demote():os.initgroups(u.pw_name,u.pw_gid);os.setgid(u.pw_gid);os.setuid(u.pw_uid)
desktop=[]
for p in Path('/proc').glob('[0-9]*'):
 try:
  if (p/'comm').read_text().strip()=='phosh' and int((p/'status').read_text().split('Uid:',1)[1].split()[0])==10000:desktop.append(p)
 except OSError:pass
assert len(desktop)==1
inherited={k.decode():v.decode() for x in (desktop[0]/'environ').read_bytes().split(b'\0') if b'=' in x for k,v in [x.split(b'=',1)]}
env={k:v for k,v in inherited.items() if k in ['HOME','USER','LOGNAME','LANG','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','WAYLAND_DISPLAY','DISPLAY','XDG_DATA_DIRS','XDG_CONFIG_DIRS']}
env.update(PATH='/usr/sbin:/usr/bin:/sbin:/bin',GSK_RENDERER='cairo',GDK_DISABLE='gl,vulkan,offload',GDK_DEBUG='dmabuf')
inner=r"""
import gi,json
gi.require_version('Gtk','4.0');gi.require_version('Gdk','4.0')
from gi.repository import Gtk,Gdk
Gtk.init();d=Gdk.Display.get_default();formats=d.get_dmabuf_formats()
print(json.dumps(dict(gtk_version=[Gtk.get_major_version(),Gtk.get_minor_version(),Gtk.get_micro_version()],dmabuf_format_count=formats.get_n_formats(),formats=[list(formats.get_format(i)) for i in range(formats.get_n_formats())])))
"""
p=subprocess.run(['/usr/bin/python3','-c',inner],env=env,preexec_fn=demote,capture_output=True,timeout=12)
out=r/'k240-gtk-cpu-dmabuf';assert not out.exists();out.mkdir(mode=0o700)
(out/'stdout-private.json').write_bytes(p.stdout);(out/'stderr-private.txt').write_bytes(p.stderr)
assert p.returncode==0,'Read format API diagnostic before retry'
data=json.loads(p.stdout);data.update(stage=240,no_camera_stream=True,cairo_renderer='requested',gl_and_vulkan_disabled=True)
(out/'summary.json').write_text(json.dumps(data,indent=2)+'\n');print(json.dumps(data))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=20)
(host.PRIVATE/'gtk-cpu-dmabuf-host-private.log').write_bytes(p.stdout+p.stderr)
data=json.loads(p.stdout);(R/'gtk-cpu-dmabuf-validation.json').write_text(json.dumps(data,indent=2)+'\n')
print(json.dumps(data))
