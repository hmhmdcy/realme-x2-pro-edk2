from pathlib import Path
import ast
r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel134'
assert not (ref / 'collect-recovered-runtime.sh').exists()
t = (ref / 'collect-runtime.sh').read_text().replace('k134-first-runtime', 'k134-recovered-runtime').replace('KERNEL134_FIRST', 'KERNEL134_RECOVERED')
t = t.replace('grep -q', 'grep -q', 1)
(ref / 'collect-recovered-runtime.sh').write_text(t)
t = (ref / 'inspect-runtime.py').read_text().replace('first-runtime-private.tar.gz', 'recovered-runtime-private.tar.gz')
ast.parse(t)
(ref / 'inspect-recovered-runtime.py').write_text(t)
print('K134_POST_RECOVERY_READONLY_RUNTIME_CAPTURE_KEEPS_FAILED_FIRST_CAPTURE_READY', flush=True)
