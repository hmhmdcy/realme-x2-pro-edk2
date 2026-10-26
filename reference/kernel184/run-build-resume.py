from pathlib import Path
import host
path = Path(__file__).resolve().parent / 'resume-libssc-build.py'
extra = list((host.PRIVATE / 'deps-apks-private').glob('util-linux-dev-*.apk'))
assert len(extra) == 1
host.upload(extra[0], '/var/lib/samurai/k184-libssc-deps-apks/' + extra[0].name)
host.upload(path, '/var/lib/samurai/k184-tools/resume-libssc-build-r4.py')
result = host.ssh('nohup python3 /var/lib/samurai/k184-tools/resume-libssc-build-r4.py > /var/lib/samurai/k184-libssc-r4-worker-private.log 2>&1 < /dev/null & echo $!')
(host.PRIVATE / 'libssc-r4-worker-pid-private.txt').write_bytes(result.stdout)
print('Native SDK Python path corrected; build resumed with previous failure logs retained.')
