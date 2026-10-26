from pathlib import Path
import json,subprocess,time
import host,storage
HERE=Path(__file__).resolve().parent;start=time.monotonic()
with storage.sdk_candidate():
    q=subprocess.run(['chroot',str(storage.SDK),'ninja','-C','/work/libcamera/src/libcamera-v0.7.2/output','-j4','src/libcamera/libcamera.so.0.7.2'],capture_output=True)
(host.PRIVATE/'candidate-build.log').write_bytes(q.stdout+q.stderr)
report=dict(stage=387,component='camss_ipe_pipeline',exit_code=q.returncode,seconds=round(time.monotonic()-start,2),installed=False,sdk_bind_unmounted=True,passed=q.returncode==0)
(HERE/'build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print((q.stdout+q.stderr).decode()[-4000:]);print(json.dumps(report));assert not q.returncode
