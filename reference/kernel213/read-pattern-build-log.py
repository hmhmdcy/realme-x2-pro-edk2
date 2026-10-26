from pathlib import Path
import host
code=r'''
from pathlib import Path
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k213-baseline/boot-id-private.txt').read_bytes()
path=root/'k213-libcamera-build/compile-pattern-probe-private.log';print('\n'.join(path.read_text(errors='replace').splitlines()[-55:]))
'''
print(host.ssh('python3 -',input=code.encode(),timeout=30).stdout.decode())
