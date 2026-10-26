from pathlib import Path
import hashlib
import json
import os
import subprocess
import tempfile

os.umask(0o077)
out = Path('/var/lib/samurai/k186-candidate-failure')
out.mkdir(mode=0o700)
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == Path('/var/lib/samurai/k186-reboot-runtime/boot-id-private.txt').read_bytes()
progress = json.loads(Path('/var/lib/samurai/k186-original-cycles/progress.json').read_text())
assert len(progress) == 1 and progress[0]['fault_delta']['pool_reclaim'] == 1
assert Path('/sys/class/remoteproc/remoteproc0/state').read_text().strip() == 'offline'
assert Path('/sys/devices/platform/sensor-power/state').read_text().strip() == 'vdd=0 vddio=0'
target = Path('/usr/lib/modules') / os.uname().release / 'kernel/drivers/misc/fastrpc.ko'
candidate_sha = '95c9e2b04ae3672048e330c8502dd490ac5e867187283dacd58b2cd50875ae47'
assert hashlib.sha256(target.read_bytes()).hexdigest() == candidate_sha
original = Path('/var/lib/samurai/k186-load-fastrpc-r2/fastrpc-original-private.ko').read_bytes()
assert hashlib.sha256(original).hexdigest() == '4515b1b22f212ce2ec482039343d9b72193ef2100e8b0b97227bdde2f37156aa'
st = target.stat()
fd, temporary = tempfile.mkstemp(prefix='.k186-rollback-', dir=target.parent)
try:
    with os.fdopen(fd,'wb') as f:
        f.write(original);f.flush();os.fsync(f.fileno())
    os.chmod(temporary,st.st_mode & 0o777)
    os.chown(temporary,st.st_uid,st.st_gid)
    os.replace(temporary,target)
finally:
    if os.path.exists(temporary):os.unlink(temporary)
(out/'boot-id-private.txt').write_bytes(boot)
report = dict(stage=186,candidate_first_full_light_trial_passed=True,
    candidate_reserved_pool_reclaim_failed=True,original_default_module_file_restored=True,
    loaded_candidate_retained_until_controlled_reset=True,no_force_unload=True,
    slpi_offline=True,sensor_supplies_off=True,taint=int(Path('/proc/sys/kernel/tainted').read_text()),
    no_repeat_of_remaining_two_cycles=True,permanent_fix_accepted=False)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
os.sync()
print(json.dumps(report))
