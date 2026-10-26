from pathlib import Path
import hashlib, host, json
build = host.PRIVATE / 'tftp-build-r5'
files = ['samurai-tqftpserv-isolated', 'test-tftp-ram-arm64', 'test-tftp-qrtr-arm64']
out = '/var/lib/samurai/k206-tftp-isolated'
code = "from pathlib import Path; import os; os.umask(0o077); assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k205r2-runtime/boot-id-private.txt').read_bytes(); Path(" + repr(out) + ").mkdir(mode=0o700)"
host.ssh('python3 -', input=code.encode())
digests = {}
for name in files:
    host.upload(build / name, out + '/' + name)
    digests[name] = hashlib.sha256((build / name).read_bytes()).hexdigest()
code = "from pathlib import Path; import json; p=Path(" + repr(out) + "); d=" + repr(digests) + "; [(p/n).chmod(0o700) for n in d]; (p/'artifacts-private.json').write_text(json.dumps(d)+'\\n')"
host.ssh('python3 -', input=code.encode())
print('Three native test artifacts staged; production TFTP service unchanged.')
