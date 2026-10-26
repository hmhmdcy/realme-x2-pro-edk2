"""Preserve the proven unstarted, incomplete R4 extraction before retry."""
from pathlib import Path
import shlex,tarfile
import host
with tarfile.open(host.PRIVATE/'probe.tar.gz','r:gz') as archive:
 names=archive.getnames();assert 'worker.py' in names and any(n.startswith('ipa/') and n.endswith('.sign') for n in names)
code='''
from pathlib import Path
root=Path('/var/lib/samurai/k341-dynamic-lsc-r4');backup=root.with_name(root.name+'-incomplete-transfer')
assert root.resolve()==root and root.is_dir() and not (root/'state.json').exists() and not backup.exists()
for p in Path('/proc').glob('[0-9]*'):
 try:
  args=(p/'cmdline').read_bytes().split(b'\\0')
  assert str(root/'worker.py').encode() not in args,'A worker is live'
 except (FileNotFoundError,ProcessLookupError):pass
root.rename(backup)
print('Preserved unstarted partial extraction; current complete archive may be launched.')
'''
print(host.raw_ssh('python3 -c '+shlex.quote(code),timeout=20).stdout.decode())
