"""Pinned0.57 release + fixed Alpine prepare + frozen five-file patch, private native-musl build."""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import subprocess
import tarfile
import time

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
BASE=Path('/home/cy122/charging-management-20261023/phosh-external-power-build-501-r1')
ROOT=BASE/'root'
SOURCE=ROOT/'work/source/phosh-0.57.0'
ORIGINAL=REPO/'reference/charging-ui-audit-20261023/phosh-connection-source-r8'
CANDIDATE=REPO/'reference/charging-ui-audit-20261023/phosh-external-power-candidate-r1'
sha=lambda b:hashlib.sha256(b).hexdigest()
assert json.loads((HERE/'feedback-interfaces-result.json').read_bytes())['runtime_original_bytes_retained']
assert not SOURCE.exists()
archive=Path('/mnt/e/edk2-samurai-out/charging-ui-audit-20261023/phosh-connection-source-r8/phosh-0.57.0.tar.xz')
assert sha(archive.read_bytes())=='30cd0eb182b92846162ab57516170ca09fe8ce08ef95703ee351af7b9c2b9520'
with tarfile.open(archive,mode='r:xz') as t:t.extractall(ROOT/'work/source',filter='data')
patches=[ORIGINAL/'splash-timeout-flatpak-dbus.patch',CANDIDATE/'external-power-marker.patch']
patch_results=[]
for patch in patches:
    result=subprocess.run(['patch','--batch','--fuzz=0','-p1','--input',str(patch)],cwd=SOURCE,capture_output=True)
    patch_results.append({'path':str(patch),'sha256':sha(patch.read_bytes()),'returncode':result.returncode,
                          'stdout':result.stdout.decode(),'stderr':result.stderr.decode()})
    assert result.returncode==0,patch_results[-1]
meson=SOURCE/'meson.build';original_meson=meson.read_bytes()
meson.write_bytes(original_meson.replace(b'.rc',b'_rc'))
candidate=json.loads((CANDIDATE/'source-result.json').read_bytes())
for name,pin in candidate['files'].items():assert sha((SOURCE/name).read_bytes())==pin['candidate_sha256'],name
script=ROOT/'work/build-phosh-external-power.sh'
script.write_text('''#!/bin/sh
set -eu
export JOBS=4 CHOST=aarch64-alpine-linux-musl CBUILD=aarch64-alpine-linux-musl CARCH=aarch64
. /usr/share/abuild/default.conf
abuild-meson -Db_lto=true -Dphoc_tests=disabled -Dman=true -Dbindings-lib=true /work/source/phosh-0.57.0 /work/build/phosh-external-power
meson compile -C /work/build/phosh-external-power -j4
''')
state={'phase':'phosh-configure-build','terminal':False,'upstream_version':'0.57.0','candidate_pkgrel':3001,
       'original_package_identity_not_reused':True,'original_exact315_closure_still_failed':True,
       'private_build_input_changes':'Two signed same-source GIR1.86-r1 packages, fixed0.8.9 feedback headers/enums/pc/GIR; no phone runtime changes',
       'source_archive_sha256':sha(archive.read_bytes()),'patches':patch_results,
       'actual_five_files_equal_frozen_candidate':True,
       'meson_rc_prepare_changed_bytes':original_meson!=meson.read_bytes(),
       'source_sha256':sha(Path(__file__).read_bytes())}
marker=BASE/'phosh-build-state-private.json'
def save():marker.write_text(json.dumps(state,indent=2)+'\n')
save();start=time.monotonic()
with (BASE/'phosh-build-private.log').open('xb') as log:
    p=subprocess.Popen(['chroot',str(ROOT),'/bin/sh','/work/build-phosh-external-power.sh'],stdout=log,stderr=subprocess.STDOUT,
                       env={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','HOME':'/root','LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1'})
    state.update(pid=p.pid,argv=p.args);save();rc=p.wait()
state.update(terminal=True,returncode=rc,seconds=round(time.monotonic()-start,3),phase='phosh-build-complete' if rc==0 else 'phosh-build-failed',
             log_sha256=sha((BASE/'phosh-build-private.log').read_bytes()))
save();(HERE/'phosh-build-result.json').write_text(json.dumps(state,indent=2)+'\n')
print((BASE/'phosh-build-private.log').read_text(errors='replace')[-7500:])
print(json.dumps({'returncode':rc,'seconds':state['seconds'],'result_sha256':sha((HERE/'phosh-build-result.json').read_bytes())}))
raise SystemExit(rc)
