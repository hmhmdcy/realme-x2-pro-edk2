from pathlib import Path
import os
assert os.uname().version.startswith('#140 ')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()!=Path('/var/lib/samurai/k143-first-runtime/boot-id-private.txt').read_bytes()
print('K143_RESTORED140_BOOT_CONFIRMED')
