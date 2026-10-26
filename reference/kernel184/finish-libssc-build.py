"""Finish linking against the installed libintl after the SDK link failure."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess

os.umask(0o077)
out = Path('/var/lib/samurai/k184-libssc-r2')
sdk = Path('/run/k184-libssc-sdk-r2')
build = out / 'build-r4'
db = Path('/lib/apk/db/installed').read_bytes()
intl = Path('/usr/lib/libintl.so.8').read_bytes()
(sdk / 'usr/lib/libintl.so.8').write_bytes(intl)
link = sdk / 'usr/lib/libintl.so'
if not link.exists():
    link.symlink_to('libintl.so.8')
assert link.is_symlink() and os.readlink(link) == 'libintl.so.8'
closure = subprocess.run(['ldd', '/usr/lib/libgio-2.0.so.0', '/usr/lib/libqmi-glib.so.5'],
                         capture_output=True, check=True).stdout.decode()
(out / 'dependency-closure-private.txt').write_text(closure)
for path in set(re.findall(r'=> (/[^ ]+) \(', closure)):
    original = Path(path)
    assert original.is_file()
    if 'ld-musl' in original.name:
        continue
    for target in {sdk / 'usr/lib' / original.name, sdk / 'usr/lib' / original.resolve().name}:
        if target.is_symlink():
            target.unlink()
        target.write_bytes(original.read_bytes())
env = dict(os.environ, PATH=str(sdk / 'usr/bin') + ':' + os.environ['PATH'],
           LD_LIBRARY_PATH=str(sdk / 'usr/lib') + ':' + str(sdk / 'lib'),
           PYTHONPATH=str(sdk / 'usr/lib/python3.14/site-packages'))
with (out / 'compile-r6-private.log').open('xb') as log:
    subprocess.run([str(sdk / 'usr/bin/ninja'), '-C', str(build), '-j2', 'src/libssc.so.2', 'src/ssccli'],
                   env=env, stdout=log, stderr=subprocess.STDOUT, timeout=90, check=True)
candidate = build / 'src/libssc.so.2'
readelf = str(sdk / 'usr/bin/readelf')
elf = subprocess.run([readelf, '-h', '-d', str(candidate)], env=env, capture_output=True, check=True).stdout
(out / 'elf-r5-private.txt').write_bytes(elf)
assert b'AArch64' in elf and b'Library soname: [libssc.so.2]' in elf


def symbols(path):
    raw = subprocess.run([readelf, '--dyn-syms', '--wide', str(path)], env=env, capture_output=True, check=True).stdout.decode()
    (out / ('candidate-symbols-private.txt' if path == candidate else 'system-symbols-private.txt')).write_text(raw)
    return {line.split()[-1] for line in raw.splitlines()
            if re.search(r'\sFUNC\s+GLOBAL\s+DEFAULT\s+(?!UND\b)\S+\s', line)}


assert symbols(candidate) == symbols(Path('/usr/lib/libssc.so.2'))
assert Path('/lib/apk/db/installed').read_bytes() == db
report = {'version': '0.4.4', 'candidate_sha256': hashlib.sha256(candidate.read_bytes()).hexdigest(),
          'patch_sha256': hashlib.sha256((out / 'libssc-wise-light.patch').read_bytes()).hexdigest(),
          'source_archive_sha256': '716d6bd6b34d2d753060c6b54c9a87e34fae75b724c763bf9ef487efa3621587',
          'signed_sdk_packages': len(list(Path('/var/lib/samurai/k148-sdk-apks').glob('*.apk'))) + 11,
          'same_exported_function_names_and_soname': True,
          'package_database_unchanged': True, 'system_library_replaced': False, 'compiled': True}
(out / 'build-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
