"""One fresh SLPI start, DSP-first stop, then one guarded restart attempt."""
from pathlib import Path
import hashlib
import json
import subprocess
import host

ref = Path(__file__).resolve().parent
value = (ref.parent / 'kernel184/test-sensor-light.sh').read_text()
value = value.replace('k184-baseline-r2/boot-id-private.txt', 'k186-baseline/boot-id-private.txt')
value = value.replace('ram-k184-light-v1', 'ram-k186-lifecycle')
value = value.replace('k184-sensor-light-v1', 'k186-slpi-lifecycle')
value = value.replace('pidof hexagonrpcd)', 'pidof hexagonrpcd hexagonrpcd-v5)')
# Normal cleanup keeps the file service alive until the root DSP has stopped.
begin = value.index('    if [ -n "$owner" ] && kill -0')
middle = value.index('    if [ "$(cat "$node/state")" != offline ]; then', begin)
end = value.index('    if [ -n "$recover_owner" ]; then', middle)
daemon_stop = value[begin:middle]
dsp_stop = value[middle:end]
value = value[:begin] + dsp_stop + daemon_stop + value[end:]
value = value.replace('timeout -s TERM -k 3 110 ', 'timeout -s TERM -k 3 160 ')
start = value.index('set +e\ntimeout -s TERM -k 2 55 python3')
value = value[:start] + '''set +e
timeout -s TERM -k 2 30 python3 -B /var/lib/samurai/k186-tools/ssc-attribute-census.py --output "$dest/attributes" --duration 12 > "$dest/census-host-private.txt" 2>&1
query=$?
set -e
printf '%s\\n' "$query" > "$dest/census-exit.txt"
test "$(cat "$node/state")" = running
kill -0 "$owner"
dmesg > "$dest/first-running-dmesg-private.txt"
cat /proc/interrupts > "$dest/first-running-interrupts-private.txt"
# Stop the DSP while its file server is still registered and alive.
cat /proc/uptime > "$dest/stop1-uptime-private.txt"
set +e
timeout -s TERM -k 2 12 sh -c 'echo stop > "$1/state"' sh "$node" > "$dest/stop1-private.txt" 2>&1
stopped=$?
set -e
printf '%s\\n' "$stopped" > "$dest/stop1-exit.txt"
cat "$node/state" > "$dest/state-after-stop1.txt"
dmesg > "$dest/after-stop1-dmesg-private.txt"
cat /proc/interrupts > "$dest/after-stop1-interrupts-private.txt"
test "$stopped" = 0 && test "$(cat "$node/state")" = offline
if kill -0 "$owner" 2>/dev/null; then kill -TERM "$owner"; fi
set +e
wait "$owner"
daemon_exit=$?
set -e
printf '%s\\n' "$daemon_exit" > "$dest/daemon1-exit.txt"
owner=
echo 0 > "$power"
test "$(cat "$power")" = 'vdd=0 vddio=0'
sleep 5
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat "$dest/boot-id-private.txt")"
test "$(cat /proc/sys/kernel/tainted)" = 0
test "$(cat "$node/state")" = offline
test "$(cat "$node/firmware")" = "$original_fw"
echo 1 > "$power"
test "$(cat "$power")" = 'vdd=1 vddio=1'
cat /proc/uptime > "$dest/restart-uptime-private.txt"
set +e
timeout -s TERM -k 2 15 sh -c 'echo start > "$1/state"' sh "$node" > "$dest/start2-private.txt" 2>&1
restarted=$?
set -e
printf '%s\\n' "$restarted" > "$dest/start2-exit.txt"
cat "$node/state" > "$dest/state-after-start2.txt"
dmesg > "$dest/after-start2-dmesg-private.txt"
cat /proc/interrupts > "$dest/after-start2-interrupts-private.txt"
if [ "$restarted" != 0 ] || [ "$(cat "$node/state")" != running ]; then
    echo DSP_FIRST_STOP_DID_NOT_RESTORE_RESTART > "$dest/restart-result.txt"
    exit 1
fi
echo DSP_FIRST_STOP_RESTART_RUNNING > "$dest/restart-result.txt"
sleep 5
qrtr-lookup > "$dest/qrtr-after-restart-private.txt"
exit 0
'''
script = ref / 'test-slpi-lifecycle.sh'
assert not script.exists()
script.write_text(value)
subprocess.run(['sh', '-n', str(script)], check=True)
host.ssh('test ! -e /var/lib/samurai/k186-tools && mkdir -m700 /var/lib/samurai/k186-tools')
for path in [script, ref.parent / 'kernel113/ssc-suid-census.py', ref.parent / 'kernel113/ssc-attribute-census.py']:
    host.upload(path, '/var/lib/samurai/k186-tools/' + path.name)
    host.ssh('sha256sum -c -', input=(hashlib.sha256(path.read_bytes()).hexdigest() +
             '  /var/lib/samurai/k186-tools/' + path.name + '\n').encode())
report = dict(stage=186, script_sha256=hashlib.sha256(script.read_bytes()).hexdigest(),
    kernel_build=183, first_start_on_current_boot=True, dsp_stopped_before_file_service=True,
    restart_attempts=1, stock_firmware_only=True, registry_writes_only_in_ram=True,
    no_sensor_measurement_requests=True, no_reboot_or_flash=True)
(ref / 'lifecycle-preparation.json').write_text(json.dumps(report, indent=2) + '\n')
p = host.ssh('nohup sh /var/lib/samurai/k186-tools/test-slpi-lifecycle.sh > /var/lib/samurai/k186-lifecycle-worker-private.log 2>&1 < /dev/null & echo $!')
(host.PRIVATE / 'lifecycle-worker-pid-private.txt').write_bytes(p.stdout)
print(json.dumps(report))
