from pathlib import Path
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
text=(ref/'test-sensor-ram-v8.sh').read_text()
text=text.replace('k113-reboot-radio-clean-3/','k113-reboot-radio-clean-4/')
text=text.replace('ram-v8','ram-v9').replace('RAM_V8','RAM_V9')
text=text.replace('timeout -s TERM -k 3 150 ', 'timeout -s TERM -k 3 240 ')
text=text.replace('owner=\nfinish()', 'owner=\nrecover_owner=\nfinish()', 1)
text=text.replace('    cat "$node/state" > "$dest/slpi-final-state.txt"', '''    if [ -n "$recover_owner" ]; then
        wait "$recover_owner"
        recover_owner=
    fi
    cat "$node/state" > "$dest/slpi-final-state.txt"''', 1)
text=text.replace('    cat "$power" > "$dest/power-final.txt"', '''    if [ "$(cat "$node/state")" = offline ]; then echo disabled > "$node/coredump"; fi
    cat "$power" > "$dest/power-final.txt"''', 1)
start=text.index('owner=$!\nsleep 60')
end=text.index('wait "$owner"',start)
text=text[:start]+'''owner=$!
sleep 20
printf 'PROXIMITY_COVER_WINDOW_OPEN_120_SECONDS\\n'
cat /proc/uptime > "$dest/proximity-window-uptime.txt"
set +e
timeout -s TERM -k 2 128 ssccli --debug --sensor proximity --timeout 120 > "$dest/proximity.txt" 2>&1
printf '%s\\n' "$?" > "$dest/proximity-exit.txt"
printf 'PROXIMITY_COVER_WINDOW_CLOSED\\n'
timeout -s TERM -k 2 18 ssccli --debug --sensor accelerometer --timeout 10 > "$dest/accelerometer.txt" 2>&1
query=$?
for kind in light magnetometer; do
    if ! kill -0 "$owner" 2>/dev/null; then break; fi
    timeout -s TERM -k 2 18 ssccli --debug --sensor "$kind" --timeout 10 > "$dest/$kind.txt" 2>&1
    printf '%s\\n' "$?" > "$dest/$kind-exit.txt"
done
''' +text[end:]
# Collect one DSP coredump through the kernel's existing supported API.
# 'recover' is explicit; automatic recovery remains disabled throughout.
# enabled mode copies memory, so a pending reader cannot hold the rproc lock.
anchor='printf \'SENSOR_QUERY_EXIT=%s RPCD_EXIT=%s\\n\' "$query" "$daemon"'
assert text.count(anchor)==1
text=text.replace(anchor,'''printf 'SENSOR_QUERY_EXIT=%s RPCD_EXIT=%s\\n' "$query" "$daemon"
test "$(cat "$node/state")" = running
test "$(cat "$node/recovery")" = disabled
test -z "$(find /sys/class/devcoredump -maxdepth 1 -name 'devcd*' -print)"
echo enabled > "$node/coredump"
cat "$node/coredump" > "$dest/coredump-mode.txt"
sync
printf 'SLPI_COREDUMP_CAPTURE_BEGIN\\n'
echo 1 > /sys/kernel/debug/remoteproc/remoteproc0/crash
i=0
while [ "$(cat "$node/state")" != crashed ] && [ "$i" -lt 40 ]; do
    sleep 0.25; i=$((i+1))
done
test "$(cat "$node/state")" = crashed
timeout -s TERM -k 3 60 sh -c 'echo recover > "$1/recovery"' sh "$node" > "$dest/recover.txt" 2>&1 &
recover_owner=$!
i=0
while [ -z "$(find /sys/class/devcoredump -maxdepth 1 -name 'devcd*' -print)" ] && [ "$i" -lt 100 ]; do
    sleep 0.25; i=$((i+1))
done
dump_node=$(find /sys/class/devcoredump -maxdepth 1 -name 'devcd*' -print)
if [ -n "$dump_node" ] && [ "$(printf '%s\\n' "$dump_node" | wc -l)" = 1 ]; then
    readlink -f "$dump_node/failing_device" > "$dest/coredump-device-private.txt"
    case "$(cat "$dest/coredump-device-private.txt")" in
        */2400000.remoteproc/remoteproc/remoteproc0) ;;
        *) echo WRONG_COREDUMP_DEVICE > "$dest/coredump-error.txt"; exit 1 ;;
    esac
    timeout -s TERM -k 2 25 cat "$dump_node/data" > "$dest/slpi-coredump.elf"
    printf '%s\\n' "$?" > "$dest/coredump-read-exit.txt"
    test "$(head -c 4 "$dest/slpi-coredump.elf" | od -An -tx1 | tr -d ' \\n')" = 7f454c46
    wc -c < "$dest/slpi-coredump.elf" > "$dest/coredump-size.txt"
    sha256sum "$dest/slpi-coredump.elf" > "$dest/coredump.sha256"
    echo 1 > "$dump_node/data"
else
    echo NO_SINGLE_COREDUMP > "$dest/coredump-error.txt"
fi
set +e
wait "$recover_owner"
printf '%s\\n' "$?" > "$dest/recover-exit.txt"
recover_owner=
set -e
cat "$node/state" > "$dest/slpi-state-after-coredump.txt"
echo disabled > "$node/recovery"
if [ "$(cat "$node/state")" != crashed ]; then echo disabled > "$node/coredump"; fi
printf 'SLPI_COREDUMP_CAPTURE_FINISHED\\n'
''')
(ref/'test-sensor-ram-v9.sh').write_text(text)
print('RAM_V9_GUARDED_PHYSICAL_PROXIMITY_AND_ONE_EXPLICIT_DSP_COREDUMP_PREPARED')
