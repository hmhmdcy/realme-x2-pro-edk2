"""Build the isolated candidate with the actual Alpine ARM64 SDK."""
from pathlib import Path
import json,subprocess,time
import host,storage
HERE=Path(__file__).resolve().parent;start=time.monotonic()
with storage.sdk_candidate():
    q=subprocess.run(['chroot',str(storage.SDK),'ninja','-C','/work/libcamera/src/libcamera-v0.7.2/output','-j4','src/libcamera/libcamera.so.0.7.2'],capture_output=True)
(host.PRIVATE/'candidate-build.log').write_bytes(q.stdout+q.stderr)
r=dict(stage=418,component='camss_ipe_media_request',exit_code=q.returncode,seconds=round(time.monotonic()-start,2),installed=False,sdk_bind_unmounted=True,passed=q.returncode==0)
(HERE/'build-validation.json').write_text(json.dumps(r,indent=2)+'\n');print((q.stdout+q.stderr).decode()[-4000:]);print(json.dumps(r));assert not q.returncode
