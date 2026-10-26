"""Build fixed0.8.9 interfaces in the one private root; keep verified feedback runtime byte-identical."""
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
BASE=Path('/home/cy122/charging-management-20261023/phosh-external-power-build-501-r1')
ROOT=BASE/'root'
sha=lambda b:hashlib.sha256(b).hexdigest()
inputs=json.loads((HERE/'three-inputs-result.json').read_bytes())
archive=Path(inputs['feedbackd_source']['path'])
assert sha(archive.read_bytes())==inputs['feedbackd_source']['sha256']
source=ROOT/'work/source/feedbackd-0.8.9'
assert not source.exists()
with tarfile.open(archive,mode='r:xz') as t:t.extractall(ROOT/'work/source',filter='data')
runtime=ROOT/'usr/lib/libfeedback-0.0.so.0'
runtime_before=runtime.read_bytes()
script=ROOT/'work/build-feedback-interfaces.sh'
script.write_text('''#!/bin/sh
set -eu
export JOBS=4 CHOST=aarch64-alpine-linux-musl CBUILD=aarch64-alpine-linux-musl CARCH=aarch64
. /usr/share/abuild/default.conf
abuild-meson -Db_lto=true -Ddaemon=false -Dtests=false -Dgtk_doc=false -Dman=false -Dvapi=false -Dudev=false -Dintrospection=enabled /work/source/feedbackd-0.8.9 /work/build/feedbackd-interfaces
meson compile -C /work/build/feedbackd-interfaces -j4
''')
state={'phase':'building-feedback-interfaces','terminal':False,'source_version':'0.8.9',
       'runtime_sha256_before':sha(runtime_before),'source_archive_sha256':sha(archive.read_bytes()),
       'scope':'Private headers/enums/pkgconfig/GIR only; no daemon or phone runtime install',
       'source_sha256':sha(Path(__file__).read_bytes())}
marker=BASE/'feedback-interface-build-state-private.json'
def save():marker.write_text(json.dumps(state,indent=2)+'\n')
save();started=time.monotonic()
with (BASE/'feedback-interface-build-private.log').open('xb') as log:
    p=subprocess.Popen(['chroot',str(ROOT),'/bin/sh','/work/build-feedback-interfaces.sh'],stdout=log,stderr=subprocess.STDOUT,
                       env={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','HOME':'/root','LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1'})
    state.update(pid=p.pid,argv=p.args);save();rc=p.wait()
state.update(terminal=True,returncode=rc,seconds=round(time.monotonic()-started,3),phase='build-complete' if rc==0 else 'build-failed')
save()
if rc:
    print((BASE/'feedback-interface-build-private.log').read_text(errors='replace')[-6500:]);raise SystemExit(rc)
build=ROOT/'work/build/feedbackd-interfaces'
temporary=build/'libfeedback/libfeedback-0.0.so.0'
def exports(path):
    p=subprocess.run(['readelf','--dyn-syms','--wide',str(path)],capture_output=True,check=True)
    return sorted(set(re.findall(r'\b(lfb_[A-Za-z0-9_]+)(?:@[^ ]*)?$',p.stdout.decode(),re.M)))
old_exports,new_exports=exports(runtime),exports(temporary)
assert old_exports and old_exports==new_exports,(old_exports,new_exports)
assert runtime.read_bytes()==runtime_before
dest=ROOT/'usr/include/libfeedback-0.0';dest.mkdir(exist_ok=True)
mapping={source/'libfeedback'/name:dest/name for name in ['libfeedback.h','lfb-event.h','lfb-main.h']}
mapping.update({build/'libfeedback/lfb-enums.h':dest/'lfb-enums.h',build/'data/lfb-gdbus.h':dest/'lfb-gdbus.h',
                build/'meson-private/libfeedback-0.0.pc':ROOT/'usr/lib/pkgconfig/libfeedback-0.0.pc',
                build/'libfeedback/Lfb-0.0.gir':ROOT/'usr/share/gir-1.0/Lfb-0.0.gir'})
generated={}
for source_file,destination in mapping.items():
    assert source_file.is_file(),source_file
    assert not destination.exists(),destination
    shutil.copy2(source_file,destination)
    generated[str(destination.relative_to(ROOT))]=sha(destination.read_bytes())
link=ROOT/'usr/lib/libfeedback-0.0.so';assert not link.exists();link.symlink_to('libfeedback-0.0.so.0')
assert runtime.read_bytes()==runtime_before
p=subprocess.run(['chroot',str(ROOT),'pkg-config','--modversion','libfeedback-0.0'],capture_output=True)
assert p.returncode==0 and p.stdout.strip()==b'0.8.9'
state.update(phase='development-interfaces-ready',generated=generated,exported_lfb_symbols=old_exports,
             runtime_original_bytes_retained=True,runtime_sha256_after=sha(runtime.read_bytes()),
             temporary_built_library_not_used_for_phosh_link=True,phone_runtime_payload_includes_these_tools=False,
             log_sha256=sha((BASE/'feedback-interface-build-private.log').read_bytes()))
save();(HERE/'feedback-interfaces-result.json').write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps({'returncode':rc,'seconds':state['seconds'],'lfb_export_count':len(old_exports),
                  'runtime_retained':True,'result_sha256':sha((HERE/'feedback-interfaces-result.json').read_bytes())},indent=2))
