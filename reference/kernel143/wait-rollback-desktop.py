from pathlib import Path
import os
import subprocess
import time
boot=Path('/var/lib/samurai/k143-rollback140-runtime/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#140 ')
for _ in range(60):
    assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==boot
    if all(subprocess.run(['pgrep','-x',name],capture_output=True).returncode==0 for name in ['phosh','phoc']):
        print('K143_RESTORED140_DESKTOP_PRESENT_READY_FOR_PASSIVE_OBSERVATION');break
    time.sleep(2)
else:raise RuntimeError('Automatic desktop not ready; inspect without replaying startup')
