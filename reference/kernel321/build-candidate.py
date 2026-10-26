"""Build the new IPA against retained r25 objects and restore the SDK work."""
from pathlib import Path
import json,os,subprocess,time
import host
HERE=Path(__file__).resolve().parent;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
work=SDK/'work/libcamera';retained=SDK/'work/libcamera321-lsc-built';snapshot=SDK/'private/libcamera-before321'
assert work.is_dir() and retained.is_dir() and not snapshot.exists()
for p in Path('/proc').glob('[0-9]*'):
 try:
  if (p/'comm').read_text().strip() in ['ninja','meson','abuild','cc1plus'] and (p/'cwd').resolve().is_relative_to(work):raise RuntimeError('Existing SDK build is live')
 except (FileNotFoundError,ProcessLookupError):pass
attempt=1
while (host.PRIVATE/f'build-r{attempt}.log').exists():attempt+=1
marker=host.PRIVATE/'build-state.json';state=dict(stage=321,pid=os.getpid(),terminal=False)
def save(**kw):state.update(kw);marker.write_text(json.dumps(state,indent=2)+'\n')
save(phase='preparing');start=time.monotonic();os.rename(work,snapshot)
try:
 os.rename(retained,work)
 with (host.PRIVATE/f'build-r{attempt}.log').open('xb') as log:
  child=subprocess.Popen(['chroot',str(SDK),'ninja','-C','/work/libcamera/src/libcamera-v0.7.2/output','-j4','src/ipa/camss-vfe/ipa_camss_vfe.so.sign'],stdout=log,stderr=subprocess.STDOUT)
  save(phase='building',child_pid=child.pid,log=str(log.name));code=child.wait()
finally:
 if work.exists():os.rename(work,retained)
 if snapshot.exists():os.rename(snapshot,work)
 save(original_work_restored=work.is_dir() and not snapshot.exists())
report=dict(stage=321,attempt=attempt,exit_code=code,seconds=round(time.monotonic()-start,2),original_work_restored=state['original_work_restored'],installed=False)
(HERE/'build-validation.json').write_text(json.dumps(report,indent=2)+'\n');save(phase='complete' if not code else 'failed',terminal=True,**report)
print((host.PRIVATE/f'build-r{attempt}.log').read_text(errors='replace')[-5000:]);print(json.dumps(report,indent=2))
raise SystemExit(code)
