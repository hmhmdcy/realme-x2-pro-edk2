from pathlib import Path
import difflib
import hashlib
import json
import os
import subprocess
import tarfile
import shutil
import re

os.umask(0o077)
out = Path('/var/lib/samurai/k184-libssc-repro')
out.mkdir(mode=0o700)
sdk = Path('/run/k184-libssc-repro-sdk')
sdk.mkdir(mode=0o755)
assert os.uname().version.startswith('#183 ')
assert Path('/sys/class/remoteproc/remoteproc0/state').read_text().strip() == 'offline'
db = Path('/lib/apk/db/installed').read_bytes()
apks = Path('/var/lib/samurai/k184-libssc-deps-apks')


def run(command, name, *, timeout=180, env=None):
    print(name, flush=True)
    with (out / (name + '-private.log')).open('wb') as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=timeout, env=env, check=True)


cached = Path('/var/lib/samurai/k148-sdk-apks')
packages = sorted(cached.glob('*.apk')) + sorted(apks.glob('*.apk'))
assert len(list(apks.glob('*.apk'))) == 11
for i, p in enumerate(packages):
    run(['apk', 'verify', str(p)], 'verify-' + str(i), timeout=30)
    run(['apk', 'extract', '--force-overwrite', '--destination', str(sdk), str(p)], 'extract-' + str(i), timeout=60)
# Link against the versions already running on the handset, not newer SDK libs.
runtime = ['libglib-2.0.so.0', 'libgobject-2.0.so.0', 'libgio-2.0.so.0', 'libgmodule-2.0.so.0',
           'libqmi-glib.so.5', 'libmbim-glib.so.4', 'libqrtr-glib.so.0', 'libprotobuf-c.so.1',
           'libpcre2-8.so.0', 'libffi.so.8', 'libz.so.1', 'libintl.so.8']
runtime_hashes = {}
for name in runtime:
    original = Path('/usr/lib') / name
    assert original.is_file()
    raw = original.read_bytes()
    runtime_hashes[name] = hashlib.sha256(raw).hexdigest()
    for target in {sdk / 'usr/lib' / name, sdk / 'usr/lib' / original.resolve().name}:
        if target.is_symlink():
            target.unlink()
        target.write_bytes(raw)
(out / 'runtime-libraries-private.json').write_text(json.dumps(runtime_hashes, indent=2) + '\n')
(sdk / 'usr/lib/libintl.so').symlink_to('libintl.so.8')
closure = subprocess.run(['ldd', '/usr/lib/libgio-2.0.so.0', '/usr/lib/libqmi-glib.so.5'],
                         capture_output=True, check=True).stdout.decode()
(out / 'dependency-closure-private.txt').write_text(closure)
for name in set(re.findall(r'=> (/[^ ]+) \(', closure)):
    original = Path(name)
    if 'ld-musl' in original.name:
        continue
    for target in {sdk / 'usr/lib' / original.name, sdk / 'usr/lib' / original.resolve().name}:
        if target.is_symlink():
            target.unlink()
        target.write_bytes(original.read_bytes())
archive = Path('/var/lib/samurai/k184-tools/libssc_0.4.4.orig.tar.gz')
assert hashlib.sha256(archive.read_bytes()).hexdigest() == '716d6bd6b34d2d753060c6b54c9a87e34fae75b724c763bf9ef487efa3621587'
with tarfile.open(archive) as tar:
    tar.extractall(out / 'source', filter='data')
source = out / 'source/libssc'
file = source / 'src/libssc-sensor-light.c'
before = file.read_text()
old = 'ssc_sensor_light_new (GCancellable *cancellable, GAsyncReadyCallback callback, gpointer user_data)\n{\n'
new = old + '''\tconst gchar *data_type = g_getenv ("LIBSSC_LIGHT_DATA_TYPE");

\t/* Some OEM firmware publishes the same light protocol as wise_light. */
\tif (g_strcmp0 (data_type, "wise_light") != 0)
\t\tdata_type = "ambient_light";

'''
assert before.count(old) == 1 and before.count('SSC_SENSOR_DATA_TYPE, "ambient_light",') == 1
after = before.replace(old, new).replace('SSC_SENSOR_DATA_TYPE, "ambient_light",', 'SSC_SENSOR_DATA_TYPE, data_type,')
file.write_text(after)
(out / 'libssc-wise-light.patch').write_text(''.join(difflib.unified_diff(
    before.splitlines(True), after.splitlines(True), fromfile='a/src/libssc-sensor-light.c', tofile='b/src/libssc-sensor-light.c')))
gccdir = next((sdk / 'usr/lib/gcc').glob('aarch64-*/*'))
common = ' --sysroot=' + str(sdk) + ' -B' + str(gccdir) + '/ -B' + str(sdk / 'usr/bin') + '/'
env = dict(os.environ, PATH=str(sdk / 'usr/bin') + ':' + os.environ['PATH'],
           LD_LIBRARY_PATH=str(sdk / 'usr/lib') + ':' + str(sdk / 'lib'),
           PYTHONPATH=str(sdk / 'usr/lib/python3.14/site-packages'),
           PKG_CONFIG_SYSROOT_DIR=str(sdk),
           PKG_CONFIG_LIBDIR=str(sdk / 'usr/lib/pkgconfig') + ':' + str(sdk / 'usr/share/pkgconfig'),
           CC=str(sdk / 'usr/bin/gcc') + common,
           LDFLAGS='-L/usr/lib -Wl,-rpath-link,' + str(sdk / 'usr/lib'))
run([str(sdk / 'usr/bin/meson'), 'setup', str(out / 'build'), str(source),
     '--buildtype=release', '-Dwarning_level=2'], 'configure', env=env)
run([str(sdk / 'usr/bin/ninja'), '-C', str(out / 'build'), '-j2', 'src/libssc.so.2', 'src/ssccli'], 'compile', env=env)
assert Path('/lib/apk/db/installed').read_bytes() == db
candidate = out / 'build/src/libssc.so.2'
assert candidate.is_file()
run([str(sdk / 'usr/bin/readelf'), '-h', '-d', str(candidate)], 'elf', env=env)
report = {'version': '0.4.4', 'source_archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
          'candidate_sha256': hashlib.sha256(candidate.read_bytes()).hexdigest(),
          'patch_sha256': hashlib.sha256((out / 'libssc-wise-light.patch').read_bytes()).hexdigest(),
          'signed_sdk_packages': len(packages), 'package_database_unchanged': True,
          'system_library_replaced': False, 'compiled': True}
(out / 'build-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
