"""Prepare a bounded kernel183 trial from the reviewed RAM-only SSC setup."""
from pathlib import Path
import hashlib
import json
import subprocess
import argparse
import host

parser = argparse.ArgumentParser()
parser.add_argument('--start', action='store_true')
args = parser.parse_args()

ref = Path(__file__).resolve().parent
text = (ref.parent / 'kernel113/test-sensor-ram-attributes15.sh').read_text()
text = text[:text.index("echo '2a7105d49d069fa375")]
text = text.replace("'^#113 '", "'^#183 '")
text = text.replace('k113-reboot-audio-clean-15/boot-id-private.txt', 'k184-baseline-r2/boot-id-private.txt')
text = text.replace('ram-attributes15', 'ram-k184-light-v1')
text = text.replace('k113-sensor-ram-k184-light-v1', 'k184-sensor-light-v1')
text = text.replace('test ! -e /dev/fastrpc-sdsp\n', '')
start = text.index('modules=/var/lib/samurai/k113-modules-candidate')
end = text.index('test "$(cat /sys/devices/soc0/soc_id)"', start)
text = text[:start] + 'modprobe socinfo\n' + text[end:]
text = text.replace('insmod "$modules/fastrpc.ko"', 'modprobe fastrpc')
text = text.replace('timeout -s TERM -k 3 180 ', 'timeout -s TERM -k 3 110 ')
text = text.replace('owner=\nrecover_owner=', 'original_recovery=$(cat "$node/recovery")\nowner=\nrecover_owner=')
text = text.replace('echo disabled > "$node/coredump"; fi', 'echo "$original_recovery" > "$node/recovery"; fi')
text += '''kill -0 "$owner"
set +e
timeout -s TERM -k 2 55 python3 -B /var/lib/samurai/k184-tools/ssc-light-probe.py --output "$dest/light" --duration 20 > "$dest/light-host-private.txt" 2>&1
query=$?
printf '%s\\n' "$query" > "$dest/light-exit.txt"
set -e
test "$(cat "$node/state")" = running
kill -0 "$owner"
exit "$query"
'''
text = text.replace('/tmp/k113-sensor-ram-k184-light-v1.tar', '/tmp/k184-sensor-light-v1.tar')
script = ref / 'test-sensor-light.sh'
script.write_text(text)
subprocess.run(['sh', '-n', str(script)], check=True)
digests = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [script, ref / 'ssc-light-probe.py']}
(ref / 'light-trial-preparation.json').write_text(json.dumps({'files': digests, 'kernel_build': 183,
    'stock_firmware_selected': True, 'registry_writes_only_in_ram_copy': True,
    'no_coredump_or_crash_injection': True, 'current_modules_used': True}, indent=2) + '\n')
if not args.start:
    print(json.dumps({'prepared': True, 'phone_changed': False, 'files': digests}))
    raise SystemExit(0)
host.PRIVATE.mkdir(parents=True, exist_ok=True)
host.ssh('test ! -e /var/lib/samurai/k184-tools && mkdir -m700 /var/lib/samurai/k184-tools')
for path in [script, ref / 'ssc-light-probe.py']:
    host.upload(path, '/var/lib/samurai/k184-tools/' + path.name)
checks = ''.join(digest + '  /var/lib/samurai/k184-tools/' + name + '\n' for name, digest in digests.items())
host.ssh('sha256sum -c -', input=checks.encode())
result = host.ssh("nohup sh /var/lib/samurai/k184-tools/test-sensor-light.sh > /var/lib/samurai/k184-light-worker-private.log 2>&1 < /dev/null & echo $!")
(host.PRIVATE / 'light-worker-pid-private.txt').write_bytes(result.stdout)
print(json.dumps({'prepared_and_started': True, 'current_modules_used': True, 'no_flash_or_reboot': True}))
