"""Inspect current GUI camera packages and crash evidence, without capture."""
from pathlib import Path
import json
import host

R=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,os,re,subprocess,time
os.umask(0o077);root=Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k236-runtime/boot-id-private.txt').read_bytes()
assert json.loads((root/'k240-upright-paired-r15-r2/state-private.json').read_text())['state']=='terminal'
out=root/'k240-camera-app-audit';assert not out.exists();out.mkdir(mode=0o700)
def run(args,name,timeout=12):
 p=subprocess.run(args,capture_output=True,timeout=timeout)
 (out/(name+'-private.log')).write_bytes(p.stdout+p.stderr)
 return p
apps=[]
for p in Path('/usr/share/applications').glob('*.desktop'):
 text=p.read_text(errors='replace')
 if re.search(r'camera|megapixels|snapshot|aperture|cheese|qcam',text,re.I):
  fields={k:v for line in text.splitlines() if '=' in line for k,v in [line.split('=',1)] if k in ['Name','Exec','TryExec','DBusActivatable','X-Flatpak']}
  apps.append(dict(file=p.name,fields=fields))
packages=run(['apk','info'],'packages').stdout.decode().splitlines()
camera_packages=[p for p in packages if re.search(r'camera|megapixels|snapshot|aperture|cheese|pipewire|wireplumber|gstreamer',p,re.I)]
processes=[]
for p in Path('/proc').glob('[0-9]*'):
 try:
  comm=(p/'comm').read_text().strip()
  if re.search(r'camera|megapixels|snapshot|aperture|cheese|qcam|pipewire|wireplumber|gnome-session',comm,re.I):
   processes.append(dict(pid=int(p.name),comm=comm,uid=int((p/'status').read_text().split('Uid:',1)[1].split()[0])))
 except OSError:pass
files=[]
for directory in ['/var/log','/home/user/.cache','/home/user/.local/state','/home/pmos/.cache','/home/pmos/.local/state','/home/cy122/.cache','/home/cy122/.local/state','/run/user/10000']:
 p=Path(directory)
 if not p.is_dir():continue
 for f in p.rglob('*'):
  try:
   if f.is_file() and not f.is_symlink() and f.stat().st_size<16*1024*1024 and re.search(r'log|err|crash|core',f.name,re.I):
    files.append(dict(path=str(f),bytes=f.stat().st_size))
  except OSError:pass
  if len(files)>1000:break
(out/'candidate-log-files-private.json').write_text(json.dumps(files,indent=2)+'\n')
log_paths=[Path('/var/log/messages'),Path('/home/user/.xsession-errors'),Path('/home/pmos/.xsession-errors'),Path('/home/cy122/.xsession-errors')]
matched=[]
for path in log_paths:
 if path.is_file():
  with path.open('rb') as f:
   f.seek(max(0,path.stat().st_size-2*1024*1024));data=f.read()
  lines=[line.decode(errors='replace') for line in data.splitlines() if re.search(rb'camera|megapixels|snapshot|aperture|cheese|segfault|trap|coredump|SIGSEGV|SIGABRT|libcamera',line,re.I)]
  (out/(path.name.replace('.','_')+'-camera-private.log')).write_text('\n'.join(lines[-200:])+'\n')
  matched.extend(lines[-40:])
if Path('/usr/bin/journalctl').exists():
 run(['journalctl','--no-pager','-n','200','-t','snapshot','-t','megapixels','-t','aperture'],'camera-journal')
cores=[]
for directory in ['/var/lib/systemd/coredump','/var/crash','/tmp']:
 p=Path(directory)
 if p.exists():
  cores += [dict(path=str(f),bytes=f.stat().st_size) for f in p.iterdir() if f.is_file() and re.search(r'core|crash',f.name,re.I)]
report=dict(stage=240,desktop_camera_apps=apps,camera_related_packages=camera_packages,related_processes=processes,
 crash_artifacts_found=len(cores),candidate_log_files=len(files),matching_log_lines=len(matched),
 core_pattern=Path('/proc/sys/kernel/core_pattern').read_text().strip(),no_camera_launched_or_images_saved=True)
(out/'summary-private.json').write_text(json.dumps(report,indent=2)+'\n')
(out/'camera-log-matches-private.txt').write_text('\n'.join(matched)+'\n')
(out/'crash-artifacts-private.json').write_text(json.dumps(cores,indent=2)+'\n')
print(json.dumps(report))
'''
result=host.ssh('python3 -',input=code.encode(),timeout=65)
(host.PRIVATE/'camera-app-audit-host-private.log').write_bytes(result.stdout+result.stderr)
report=json.loads(result.stdout)
(host.PRIVATE/'camera-app-audit-private.json').write_text(json.dumps(report,indent=2)+'\n')
public={k:v for k,v in report.items() if k not in ['related_processes','core_pattern']}
(R/'camera-app-audit-validation.json').write_text(json.dumps(public,indent=2)+'\n')
print(json.dumps(public))
