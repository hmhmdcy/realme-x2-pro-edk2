from pathlib import Path
import ast

r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel138'
out = Path('/mnt/e/edk2-samurai-out/kernel138')
assert not out.exists()
out.mkdir(mode=0o700)
t = (r / 'reference/kernel133/capture-charge-contract.py').read_text()
t = t.replace('k133', 'k138').replace('K133', 'K138')
t = t.replace('/var/lib/samurai/k132-first-runtime/boot-id-private.txt', '/var/lib/samurai/k137-rollback132-runtime/boot-id-private.txt')
t = t.replace('timeout=10', 'timeout=60')
ast.parse(t)
(ref / 'capture-charge-contract.py').write_text(t)
print('K138_SAME_BOOT_FIXED_READ_ONLY_CHARGER_CONTRACT_TOOLS_PREPARED', flush=True)
