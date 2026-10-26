import host
code=b'''from pathlib import Path
import json,subprocess
out=Path('/var/lib/samurai/k190-mm-build');sdk=Path('/var/lib/samurai/k190-mm-sdk')
print('candidate_exists',(out/'build/src/ModemManager').is_file())
if (out/'candidate-elf-private.log').exists():print((out/'candidate-elf-private.log').read_text()[-4200:])
p=sdk/'usr/lib/python3.14/site-packages/mesonbuild/scripts/depfixer.py'
lines=p.read_text().splitlines()
for i,line in enumerate(lines):
 if 'class Elf' in line or 'def __enter__' in line or 'def __exit__' in line or 'def remove_rpath' in line or 'def __init__' in line:
  print('\\n'.join(lines[i:i+15]))
'''
p=host.ssh('python3 -',input=code);print(p.stdout.decode())
