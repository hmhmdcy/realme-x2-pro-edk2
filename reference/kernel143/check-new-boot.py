from pathlib import Path
import os
assert os.uname().version.startswith('#143 ')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes() != Path('/var/lib/samurai/k143-preflash/boot-id-private.txt').read_bytes()
print('K143_NEW143_BOOT_CONFIRMED')
