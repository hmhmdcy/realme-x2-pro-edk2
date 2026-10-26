"""Stage source plus a signed, isolated native SDK without installing packages."""
from pathlib import Path
import hashlib
import json
import host

ref = Path(__file__).resolve().parent
archive = host.PRIVATE / 'libssc_0.4.4.orig.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest() == '716d6bd6b34d2d753060c6b54c9a87e34fae75b724c763bf9ef487efa3621587'
host.upload(archive, '/var/lib/samurai/k184-tools/libssc_0.4.4.orig.tar.gz')
deps = sorted((host.PRIVATE / 'deps-apks-private').glob('*.apk'))
assert len(deps) == 10
host.ssh('test ! -e /var/lib/samurai/k184-libssc-deps-apks && mkdir -m700 /var/lib/samurai/k184-libssc-deps-apks')
for path in deps:
    host.upload(path, '/var/lib/samurai/k184-libssc-deps-apks/' + path.name)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    host.ssh('sha256sum -c -', input=(digest + '  /var/lib/samurai/k184-libssc-deps-apks/' + path.name + '\n').encode())
host.upload(ref / 'build-libssc.py', '/var/lib/samurai/k184-tools/build-libssc-r2.py')
result = host.ssh('nohup python3 /var/lib/samurai/k184-tools/build-libssc-r2.py > /var/lib/samurai/k184-libssc-r2-worker-private.log 2>&1 < /dev/null & echo $!')
(host.PRIVATE / 'libssc-worker-pid-private.txt').write_bytes(result.stdout)
print(json.dumps({'build_started': True, 'package_installation_requested': False}))
