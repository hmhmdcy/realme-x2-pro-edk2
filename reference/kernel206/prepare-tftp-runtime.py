from pathlib import Path
import hashlib, host, json, re, subprocess
here = Path(__file__).resolve().parent
source = (host.PRIVATE / 'radio-inspection/usr__sbin__samurai-wifi-private').read_text()
assert not re.search(r'\b(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}\b', source)
assert not re.search(r'(?im)^.*(?:password|psk|ssid)\s*=\s*[^$\s]', source)
needle = '    SAMURAI_TFTP_FIRMWARE_ROOT="$base/firmware/$firmware" /usr/sbin/samurai-tqftpserv -d > "$base/tftp.log" 2>&1 &'
assert source.count(needle) == 1
text = source.replace(needle, '''    # Firmware work files are volatile and bounded independently of NV COW.
    mkdir -m 0700 "$base/tftp-rw"
    mount -t tmpfs -o size=32m,mode=0700,nosuid,nodev,noexec tmpfs "$base/tftp-rw"
    SAMURAI_TFTP_RW_ROOT="$base/tftp-rw" SAMURAI_TFTP_FIRMWARE_ROOT="$base/firmware/$firmware" /usr/sbin/samurai-tqftpserv -d > "$base/tftp.log" 2>&1 &''')
target = here.parents[1] / 'linux-port/radio/samurai-wifi.sh'
assert not target.exists()
target.write_text(text)
subprocess.run(['sh', '-n', str(target)], check=True)
out = '/var/lib/samurai/k206-tftp-stage'
code = "from pathlib import Path; import os; os.umask(0o077); assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k205r2-runtime/boot-id-private.txt').read_bytes(); Path(" + repr(out) + ").mkdir(mode=0o700)"
host.ssh('python3 -', input=code.encode())
files = {'samurai-tqftpserv-new': host.PRIVATE / 'tftp-build-r5/samurai-tqftpserv-ram', 'samurai-wifi-new.sh': target}
digests = {}
for name, path in files.items():
    host.upload(path, out + '/' + name)
    digests[name] = hashlib.sha256(path.read_bytes()).hexdigest()
code = "from pathlib import Path; import json; p=Path(" + repr(out) + "); (p/'artifacts-private.json').write_text(json.dumps(" + repr(digests) + "))"
host.ssh('python3 -', input=code.encode())
(here / 'tftp-staging-validation.json').write_text(json.dumps(dict(stage=206, files=digests, helper_syntax_passed=True, runtime_installed=False), indent=2) + '\n')
print('Runtime server and helper staged; current production files unchanged.')
