from pathlib import Path
import json,os,subprocess,time
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
attempt=1
while (P/f'build-r{attempt}.log').exists():attempt+=1
marker=P/'build-state.json';state=dict(stage=339,pid=os.getpid(),terminal=False)
def save(**kw):state.update(kw);marker.write_text(json.dumps(state,indent=2)+'\n')
save(phase='preparing');start=time.monotonic()
with storage.sdk_candidate():
 with (P/f'build-r{attempt}.log').open('xb') as log:
  child=subprocess.Popen(['chroot',str(storage.SDK),'ninja','-C','/work/libcamera/src/libcamera-v0.7.2/output','-j4','src/ipa/camss-vfe/ipa_camss_vfe.so.sign','src/libcamera/libcamera.so.0.7.2'],stdout=log,stderr=subprocess.STDOUT)
  save(phase='building',child_pid=child.pid);code=child.wait()
report=dict(stage=339,attempt=attempt,exit_code=code,seconds=round(time.monotonic()-start,2),sdk_bind_unmounted=True,installed=False)
(HERE/'build-validation.json').write_text(json.dumps(report,indent=2)+'\n');save(phase='complete' if not code else 'failed',terminal=True,**report)
print((P/f'build-r{attempt}.log').read_text(errors='replace')[-5000:]);print(json.dumps(report,indent=2));raise SystemExit(code)
