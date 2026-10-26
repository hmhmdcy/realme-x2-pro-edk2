"""Offline inspection only; never connect to the phone or modify shared sources."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

REF = Path(__file__).resolve().parent
sys.path.insert(0, str(REF.parent / 'kernel284'))
import storage

build = storage.mounted_build()
source = build.parent / 'source354'
paths = [
    source / 'drivers/power/supply/mp2650_charger.c',
    source / 'drivers/power/supply/bq27xxx_battery.c',
    source / 'include/linux/power_supply.h',
    source / 'Makefile', build / '.config', build / 'Module.symvers',
    build / 'include/config/kernel.release',
]
state = {'source': str(source), 'build': str(build), 'files': {}}
for p in paths:
    if p.is_file():
        state['files'][str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
state['head'] = subprocess.check_output(
    ['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
state['release'] = (build / 'include/config/kernel.release').read_text().strip()
REF.joinpath('baseline.json').write_text(json.dumps(state, indent=2) + '\n')
print(json.dumps(state, indent=2))
print('BUILD_DIRECTORIES', [p.name for p in build.parent.iterdir()
                            if p.name.startswith(('build', 'source'))])
print('BUILD_MAKEFILE', (build / 'Makefile').read_text()[:1000]
      if (build / 'Makefile').exists() else 'absent')
print('CONFIG', [s for s in (build / '.config').read_text().splitlines()
                 if any(x in s for x in ['MP2650', 'BQ27', 'LOCALVERSION',
                                         'MODVERSIONS', 'RANDSTRUCT', 'KASAN'])])
print('DRIVER\n', paths[0].read_text())
print(subprocess.check_output(['df', '-h', str(build.parent), '/tmp', '/home/cy122'], text=True))
