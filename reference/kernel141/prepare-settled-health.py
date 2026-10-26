from pathlib import Path
import ast

root = Path('/mnt/e/RealmeX2Pro edk2')
path = root / 'reference/kernel141/observe-settled-health.py'
assert not path.exists()
text = (root / 'reference/kernel140/observe-settled-health.py').read_text()
text = text.replace('k140-', 'k141-').replace('stage=140, current_kernel=140', 'stage=141, current_kernel=140')
assert "version.startswith('#140 ')" in text
ast.parse(text)
path.write_text(text)
print('K141_SETTLED_NEW_BOOT_PASSIVE_OBSERVER_READY')
