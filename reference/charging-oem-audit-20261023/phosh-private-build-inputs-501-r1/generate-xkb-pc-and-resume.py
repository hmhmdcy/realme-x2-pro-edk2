"""Generate only fixed2.48 pkgconfig with actual Meson; resume the known failed private Phosh build."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import time

HERE=Path(__file__).resolve().parent
BASE=Path('/home/cy122/charging-management-20261023/phosh-external-power-build-501-r1')
ROOT=BASE/'root'
sha=lambda b:hashlib.sha256(b).hexdigest()
pin=json.loads((HERE/'xkeyboard-source-result.json').read_bytes())
archive=BASE/'same-source-build-inputs/xkeyboard-config-xkeyboard-config-2.48.tar.gz'
assert sha(archive.read_bytes())==pin['sha256']
source=ROOT/'work/source/xkeyboard-config-xkeyboard-config-2.48'
assert not source.exists()
with tarfile.open(archive,mode='r:gz') as t:t.extractall(ROOT/'work/source',filter='data')
env={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','HOME':'/root','LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1'}
command=['chroot',str(ROOT),'abuild-meson','/work/source/xkeyboard-config-xkeyboard-config-2.48','/work/build/xkeyboard-pc-only']
configure=subprocess.run(command,capture_output=True,env=env)
(BASE/'xkeyboard-pc-configure-private.log').write_bytes(configure.stdout+configure.stderr)
if configure.returncode:
    print((configure.stdout+configure.stderr).decode(errors='replace')[-5000:]);raise SystemExit(configure.returncode)
pc=ROOT/'work/build/xkeyboard-pc-only/meson-private/xkeyboard-config-2.pc'
assert pc.is_file()
destination=ROOT/'usr/share/pkgconfig/xkeyboard-config-2.pc'
assert not destination.exists();shutil.copy2(pc,destination)
alias=ROOT/'usr/share/pkgconfig/xkeyboard-config.pc'
assert not alias.exists();alias.symlink_to('xkeyboard-config-2.pc')
check=subprocess.run(['chroot',str(ROOT),'pkg-config','--cflags','gnome-desktop-3.0'],capture_output=True,env=env)
assert check.returncode==0,check.stderr.decode()
record={'source_sha256':pin['sha256'],'actual_meson_generated':True,'pc_sha256':sha(pc.read_bytes()),'pc_text':pc.read_text(),
        'no_keymap_runtime_data_rebuilt_or_installed':True,'gnome_desktop_actual_cflags_rc':check.returncode,
        'configure_log_sha256':sha((BASE/'xkeyboard-pc-configure-private.log').read_bytes())}
(HERE/'xkeyboard-pc-result.json').write_text(json.dumps(record,indent=2)+'\n')
history=HERE/'history-configure01';history.mkdir()
for name in ['phosh-build-result.json','prepare-and-build-phosh.py']:(history/name).write_bytes((HERE/name).read_bytes())
(BASE/'phosh-build-failed-configure01-private.log').write_bytes((BASE/'phosh-build-private.log').read_bytes())
state=json.loads((HERE/'phosh-build-result.json').read_bytes());assert state['terminal'] and state['returncode']==1
state.update(phase='phosh-configure-build-after-fixed-xkb-pc',terminal=False,
             input_delta='Actual fixed2.48 Meson generated xkeyboard-config.pc only',
             resume_source_sha256=sha(Path(__file__).read_bytes()))
marker=BASE/'phosh-build-state-private.json'
def save():marker.write_text(json.dumps(state,indent=2)+'\n')
save();start=time.monotonic()
with (BASE/'phosh-build-after-xkb-private.log').open('xb') as log:
    p=subprocess.Popen(['chroot',str(ROOT),'/bin/sh','/work/build-phosh-external-power.sh'],stdout=log,stderr=subprocess.STDOUT,env=env)
    state.update(pid=p.pid,argv=p.args);save();rc=p.wait()
state.update(terminal=True,returncode=rc,seconds=round(time.monotonic()-start,3),phase='phosh-build-complete' if rc==0 else 'phosh-build-failed',
             log_sha256=sha((BASE/'phosh-build-after-xkb-private.log').read_bytes()))
save();(HERE/'phosh-build-after-xkb-result.json').write_text(json.dumps(state,indent=2)+'\n')
print((BASE/'phosh-build-after-xkb-private.log').read_text(errors='replace')[-6500:])
print(json.dumps({'returncode':rc,'seconds':state['seconds'],'result_sha256':sha((HERE/'phosh-build-after-xkb-result.json').read_bytes())}))
raise SystemExit(rc)
