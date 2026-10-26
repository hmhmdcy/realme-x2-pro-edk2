from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import hashlib,json,os,shutil,time
os.umask(0o077);root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k213-baseline/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
out=root/'k213-libcamera-build';out.mkdir(mode=0o700);old=root/'k190-mm-sdk';sdk=root/'k213-libcamera-sdk';assert not sdk.exists()
before=Path('/lib/apk/db/installed').read_bytes();size=sum(p.stat().st_size for p in old.rglob('*') if p.is_file() and not p.is_symlink());assert shutil.disk_usage(root).free>size+1024*1024*1024
start=time.monotonic();shutil.copytree(old,sdk,symlinks=True)
assert Path('/lib/apk/db/installed').read_bytes()==before
report=dict(stage=213,isolated_sdk_cloned=True,source_sdk_190_unchanged_by_copy=True,package_database_unchanged=True,cloned_regular_bytes=size,clone_elapsed_seconds=round(time.monotonic()-start,2),no_system_package_install=True,no_camera_stream_or_transition=True)
(out/'sdk-clone-summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=180);(host.PRIVATE/'sdk-clone-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(here/'sdk-clone-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
