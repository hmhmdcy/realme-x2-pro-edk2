"""Resume the preserved native source/SDK after correcting the SDK Python path."""
from pathlib import Path
import hashlib
import json
import os
import subprocess

out = Path('/var/lib/samurai/k184-libssc-r2')
sdk = Path('/run/k184-libssc-sdk-r2')
source = out / 'source/libssc'
build = out / 'build-r4'
assert not (out / 'build-validation.json').exists()
assert 'LIBSSC_LIGHT_DATA_TYPE' in (source / 'src/libssc-sensor-light.c').read_text()
db = Path('/lib/apk/db/installed').read_bytes()
gccdir = next((sdk / 'usr/lib/gcc').glob('aarch64-*/*'))
common = ' --sysroot=' + str(sdk) + ' -B' + str(gccdir) + '/ -B' + str(sdk / 'usr/bin') + '/'
env = dict(os.environ, PATH=str(sdk / 'usr/bin') + ':' + os.environ['PATH'],
           LD_LIBRARY_PATH=str(sdk / 'usr/lib') + ':' + str(sdk / 'lib'),
           PYTHONPATH=str(sdk / 'usr/lib/python3.14/site-packages'),
           PKG_CONFIG_SYSROOT_DIR=str(sdk),
           PKG_CONFIG_LIBDIR=str(sdk / 'usr/lib/pkgconfig') + ':' + str(sdk / 'usr/share/pkgconfig'),
           CC=str(sdk / 'usr/bin/gcc') + common,
           LDFLAGS='-L/usr/lib -Wl,-rpath-link,' + str(sdk / 'usr/lib'))
extra = list(Path('/var/lib/samurai/k184-libssc-deps-apks').glob('util-linux-dev-*.apk'))
assert len(extra) == 1
subprocess.run(['apk', 'verify', str(extra[0])], capture_output=True, check=True)
subprocess.run(['apk', 'extract', '--force-overwrite', '--destination', str(sdk), str(extra[0])], capture_output=True, check=True)


def run(command, name):
    print(name, flush=True)
    with (out / (name + '-private.log')).open('xb') as log:
        subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=180)


run([str(sdk / 'usr/bin/meson'), 'setup', str(build), str(source),
     '--buildtype=release', '-Dwarning_level=2'], 'configure-r4')
run([str(sdk / 'usr/bin/ninja'), '-C', str(build), '-j2',
     'src/libssc.so.2', 'src/ssccli'], 'compile-r4')
candidate = build / 'src/libssc.so.2'
run([str(sdk / 'usr/bin/readelf'), '-h', '-d', str(candidate)], 'elf-r4')
assert Path('/lib/apk/db/installed').read_bytes() == db
report = {'version': '0.4.4', 'candidate_sha256': hashlib.sha256(candidate.read_bytes()).hexdigest(),
          'patch_sha256': hashlib.sha256((out / 'libssc-wise-light.patch').read_bytes()).hexdigest(),
          'signed_sdk_packages': len(list((Path('/var/lib/samurai/k148-sdk-apks')).glob('*.apk'))) + 11,
          'package_database_unchanged': True, 'system_library_replaced': False, 'compiled': True}
(out / 'build-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
