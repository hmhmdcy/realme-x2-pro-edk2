"""Explicit file-level build sysroot layer, NOT a completed APK installation/315 transaction."""
from pathlib import Path
import hashlib
import json
import os
import stat
import subprocess

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'phosh-build-readiness-501'
BASE=Path('/home/cy122/charging-management-20261023/phosh-external-power-build-501-r1')
ROOT=BASE/'root'
SEED=Path('/home/cy122/x2pro-linux/libcamera214-root')
APK=Path('/home/cy122/pmos-samurai-rootfs01/work/apk.static')
KEYS=Path('/home/cy122/pmos-samurai-rootfs01/work/config_apk_keys')
sha=lambda b:hashlib.sha256(b).hexdigest()
os.umask(0o077)
assert ROOT.parent==BASE and not ROOT.is_symlink() and stat.S_IMODE(ROOT.stat().st_mode)==0o700
assert json.loads((OLD/'partial304-result.json').read_bytes())['passed_partial_identity_verification']
copy=json.loads((OLD/'private-copy-and-solver-result.json').read_bytes())
db=(ROOT/'lib/apk/db/installed').read_bytes();world=(ROOT/'etc/apk/world').read_bytes()
assert sha(db)==copy['original_db_sha256'] and sha(world)==copy['original_world_sha256']
records=json.loads((BASE/'verified304-records-private.json').read_bytes())
three=json.loads((HERE/'three-inputs-result.json').read_bytes())
records.extend(three['GIR_private_tools'])
state={'phase':'extracting-explicit-build-input-layer','terminal':False,
       'private_root':str(ROOT),'not_apk_installation':True,'exact_original_payload_count':304,
       'different_C_same_source_private_tool_count':2,'extracted':0}
marker=BASE/'input-layer-state-private.json'
prior=json.loads(marker.read_bytes())
assert prior['extracted']==61 and prior['not_apk_installation']
(BASE/'input-layer-failed-before-resume.json').write_bytes(marker.read_bytes())
state['extracted']=prior['extracted']
state['resume_after_known_extract_exit1']='diffutils existing private busybox path; official app_extract.c164 supports force-overwrite'
def save():marker.write_text(json.dumps(state,indent=2)+'\n')
save()
logs=BASE/'input-layer-logs';logs.mkdir(mode=0o700,exist_ok=True)
for p in records[state['extracted']:]:
    path=Path(p['path']);assert sha(path.read_bytes())==p['sha256']
    result=subprocess.run([str(APK),'--keys-dir',str(KEYS),'--force-overwrite','extract','--destination',str(ROOT),str(path)],capture_output=True,timeout=60)
    (logs/(p['name']+'.log')).write_bytes(result.stdout+result.stderr)
    assert result.returncode==0,(p['name'],(result.stdout+result.stderr).decode(errors='replace')[-1200:])
    state['extracted']+=1
    save()
assert (ROOT/'lib/apk/db/installed').read_bytes()==db and (ROOT/'etc/apk/world').read_bytes()==world
for source in [SEED]:
    assert sha((source/'lib/apk/db/installed').read_bytes())==copy['original_db_sha256']
    assert sha((source/'etc/apk/world').read_bytes())==copy['original_world_sha256']
# Build-only configuration: no original signing key/repository/work mounts and no Git invocation.
(ROOT/'etc/abuild.conf').write_text('JOBS=4\nMAKEFLAGS="-j4"\nNINJAFLAGS="-j4"\nSRCDEST=/work/distfiles\nREPODEST=/work/packages\n')
git=ROOT/'usr/bin/git'
if git.exists():
    disabled=ROOT/'private/inactive-git';assert not disabled.exists();git.rename(disabled)
for name in ['null','zero','random','urandom']:
    p=ROOT/'dev'/name
    minor={'null':3,'zero':5,'random':8,'urandom':9}[name]
    if not p.exists():os.mknod(p,stat.S_IFCHR|0o666,os.makedev(1,minor))
for p in ['work/distfiles','work/packages','work/source','work/build','work/stage']:(ROOT/p).mkdir(parents=True,exist_ok=True)
state.update(phase='explicit-build-input-layer-staged',terminal=True,
             original_and_private_db_world_unchanged=True,phone_or_original_runtime_changed=False,
             no_control_script_or_daemon_executed=True,no_complete_package_transaction_claim=True,
             git_hidden_in_private_copy=True,record_inputs_sha256=sha(json.dumps(records,sort_keys=True).encode()),
             source_sha256=sha(Path(__file__).read_bytes()))
save();(HERE/'input-layer-result.json').write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps(state,indent=2))
