from pathlib import Path
import os
assert os.uname().version.startswith('#145 ')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes() != Path('/var/lib/samurai/k145-preflash/boot-id-private.txt').read_bytes()
print('K145_NEW145_BOOT_CONFIRMED')
