"""Inspect an already running camera application, without starting/stopping it."""
from pathlib import Path
import json
import host
R=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,os,time,subprocess
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
out=r/'k240-existing-snapshot';assert not out.exists();out.mkdir(mode=0o700)
found=[]
for p in Path('/proc').glob('[0-9]*'):
 try:
  comm=(p/'comm').read_text().strip()
  if comm not in ['snapshot','wireplumber','pipewire','megapixels']:continue
  status=(p/'status').read_text();uid=int(status.split('Uid:',1)[1].split()[0])
  if uid!=10000:continue
  fds=[]
  for f in (p/'fd').glob('*'):
   try:s=os.readlink(f)
   except OSError:continue
   if s.startswith(('/dev/video','/dev/v4l-subdev','/dev/media')):fds.append(s)
  maps=(p/'maps').read_text()
  libs=sorted({x.split()[-1] for x in maps.splitlines() if any(y in x for y in ['/libcamera','/libgstpipewire','/libspa-libcamera','/ipa_soft','/libaperture'])})
  found.append(dict(pid=int(p.name),comm=comm,uid=uid,exe=os.readlink(p/'exe'),start_ticks=(p/'stat').read_text().rsplit(')',1)[1].split()[19],
   commandline=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace'),camera_fds=fds,mapped_camera_libraries=libs,
   log_targets={str(i):os.readlink(p/'fd'/str(i)) for i in [1,2]}))
 except (FileNotFoundError,PermissionError):pass
(out/'processes-private.json').write_text(json.dumps(found,indent=2)+'\n')
formats={}
for name in ['v4l2/vb2_v4l2_buf_done','v4l2/vb2_v4l2_dqbuf','vb2/vb2_buf_done']:
 p=Path('/sys/kernel/tracing/events',name,'format')
 if p.exists():formats[name]=p.read_text()
(out/'event-formats-private.json').write_text(json.dumps(formats,indent=2)+'\n')
logs={}
for name in ['/var/log/messages','/home/user/.local/state/phosh.log','/home/user/.local/share/xsession-errors','/home/user/.xsession-errors']:
 p=Path(name)
 if p.is_file():
  raw=p.read_bytes()[-2*1024*1024:].decode(errors='replace')
  logs[name]=[l for l in raw.splitlines() if any(s in l.lower() for s in ['snapshot','aperture','libcamera','no pipeline'])][-160:]
(out/'logs-private.json').write_text(json.dumps(logs,indent=2)+'\n')
probes={}
for bus in ['7-0010','9-0010']:
 probes[bus]=Path('/sys/bus/i2c/devices',bus,'power/runtime_status').read_text().strip()
report=dict(stage=240,applications=[dict(application=x['comm'],pid=x['pid'],start_ticks=x['start_ticks'],camera_fds=x['camera_fds'],mapped_camera_libraries=x['mapped_camera_libraries'],commandline=x['commandline'],log_targets=x['log_targets']) for x in found],
 sensor_runtime_status=probes,trace_event_formats=formats,log_sources_found=list(logs),no_app_started_or_stopped=True,
 taint=int(Path('/proc/sys/kernel/tainted').read_text()))
(out/'summary-private.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=20)
(host.PRIVATE/'existing-snapshot-host-private.log').write_bytes(q.stdout+q.stderr)
data=json.loads(q.stdout)
(host.PRIVATE/'existing-snapshot-private.json').write_text(json.dumps(data,indent=2)+'\n')
print(json.dumps(data))
