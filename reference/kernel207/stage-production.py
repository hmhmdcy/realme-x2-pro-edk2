from pathlib import Path
import hashlib, host, json
out = '/var/lib/samurai/k207-tftp-stage'
build = host.PRIVATE / 'tftp-clean-rebuild-r2'
proof = json.loads((build / 'build-validation.json').read_text())
assert proof['compiler_warnings'] == 0 and proof['patched_source_exact']
binary = build / 'samurai-tqftpserv'
assert hashlib.sha256(binary.read_bytes()).hexdigest() == proof['candidate_sha256']
code = "from pathlib import Path; import os; os.umask(0o077); assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k207-baseline/boot-id-private.txt').read_bytes(); Path(" + repr(out) + ").mkdir(mode=0o700)"
host.ssh('python3 -', input=code.encode())
host.upload(binary, out + '/samurai-tqftpserv-new')
host.upload(build / 'build-validation.json', out + '/build-validation.json')
print('Clean rebuilt production binary staged; live service unchanged.')
