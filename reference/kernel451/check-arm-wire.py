from pathlib import Path
import hashlib,json,shutil,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;storage.mount.mounted_build()
tree=storage.candidate()/'src/libcamera-v0.7.2';out=tree/'output';shutil.copyfile(HERE/'wire-contract.cpp',out/'wire-contract.cpp')
attempt=1
while (P/('arm-wire-build-r'+str(attempt)+'.log')).exists():attempt+=1
with storage.sdk_candidate():
 base='/work/libcamera/src/libcamera-v0.7.2'
 command=['chroot',str(storage.SDK),'c++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-DLIBCAMERA_BASE_PRIVATE','-include',base+'/output/config.h','-I'+base+'/include','-I'+base+'/output/include',base+'/output/wire-contract.cpp','-L'+base+'/output/src/libcamera','-lcamera','-L'+base+'/output/src/libcamera/base','-lcamera-base','-pthread','-o',base+'/output/wire-contract']
 q=subprocess.run(command,capture_output=True);(P/('arm-wire-build-r'+str(attempt)+'.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,(q.stdout+q.stderr).decode()[-4000:]
 q=subprocess.run(['chroot',str(storage.SDK),'env','LD_LIBRARY_PATH='+base+'/output/src/libcamera:'+base+'/output/src/libcamera/base',base+'/output/wire-contract'],capture_output=True)
 (P/('arm-wire-run-r'+str(attempt)+'.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,(q.stdout+q.stderr).decode()[-4000:]
 assert q.stdout.decode().count('old-decode=1 equal=1')==5
r=dict(stage=451,actual_production_fast_and_legacy_header_compiled_and_executed_arm64=True,synthetic_lengths=[0,1,16,256,6008],old_decoder_accepts_all_fast_outputs=True,wire_bytes_identical=True,header_sha256=hashlib.sha256((tree/'include/libcamera/internal/camss_byte_serializer.h').read_bytes()).hexdigest(),sdk_bind_unmounted=True,phone_accessed=False,passed=True)
(HERE/'arm-wire-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
