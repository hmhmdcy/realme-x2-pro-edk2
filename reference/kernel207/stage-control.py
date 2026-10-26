from pathlib import Path
import hashlib, host, json
build = host.PRIVATE / 'block-rollover'
out = '/var/lib/samurai/k207-tftp-isolated'
code = "from pathlib import Path; import os; os.umask(0o077); assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k207-baseline/boot-id-private.txt').read_bytes(); Path(" + repr(out) + ").mkdir(mode=0o700)"
host.ssh('python3 -', input=code.encode())
hashes = {}
for name in ['old-isolated', 'new-isolated', 'new-production', 'native-client']:
    host.upload(build / name, out + '/' + name)
    hashes[name] = hashlib.sha256((build / name).read_bytes()).hexdigest()
code = "from pathlib import Path; import json; p=Path(" + repr(out) + "); d=" + repr(hashes) + "; [(p/n).chmod(0o700) for n in d]; (p/'artifacts-private.json').write_text(json.dumps(d))"
host.ssh('python3 -', input=code.encode())
print('Four verified native artifacts staged for an isolated instance207 comparison.')
