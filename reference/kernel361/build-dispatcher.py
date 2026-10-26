from pathlib import Path
import json,subprocess,time
import host,storage
HERE=Path(__file__).resolve().parent;start=time.monotonic()
with storage.sdk_candidate():
    q=subprocess.run(['chroot',str(storage.SDK),'ninja','-C','/work/libcamera/src/libcamera-v0.7.2/output','-j4','src/libcamera/base/libcamera-base.so.0.7.2'],capture_output=True)
(host.PRIVATE/'dispatcher-build.log').write_bytes(q.stdout+q.stderr)
report=dict(stage=361,component='common_event_dispatcher',exit_code=q.returncode,seconds=round(time.monotonic()-start,2),api_and_abi_unchanged=True,installed=False,sdk_bind_unmounted=True)
(HERE/'dispatcher-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(q.stderr.decode()[-1500:]);print(json.dumps(report,indent=2));assert not q.returncode
