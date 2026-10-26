from pathlib import Path

ref = Path('/mnt/e/RealmeX2Pro edk2/reference')
text = (ref / 'kernel112/test-sensor-ram-v4.sh').read_text()
text = text.replace("'^#112 '", "'^#113 '")
text = text.replace('k112-reboot-radio-clean-2/', 'k113-first-before-slpi/')
text = text.replace('ram-v4', 'ram-v5').replace('k112-sensor-ram-v5', 'k113-sensor-ram-v5')
text = text.replace('k111-modules-candidate', 'k113-modules-candidate')
text = text.replace('daemon=$?\nset -e', 'daemon=$?\nowner=\nset -e')
anchor = 'modules=/var/lib/samurai/k113-modules-candidate\n'
assert text.count(anchor) == 1
text = text.replace(anchor, '''node=/sys/class/remoteproc/remoteproc0
power=/sys/devices/platform/sensor-power/state
test "$(cat "$power")" = 'vdd=0 vddio=0'
cat "$power" > "$dest/power-before.txt"
cat /sys/kernel/debug/regulator/regulator_summary > "$dest/regulators-before.txt"
owner=
finish() {
    code=$?
    trap - EXIT
    set +e
    if [ -n "$owner" ] && kill -0 "$owner" 2>/dev/null; then
        kill -TERM "$owner"
        wait "$owner"
    fi
    if [ "$(cat "$node/state")" != offline ]; then
        timeout -s TERM -k 2 12 sh -c 'echo stop > "$1/state"' sh "$node" > "$dest/stop.txt" 2>&1
        printf '%s\\n' "$?" > "$dest/stop-exit.txt"
    else
        echo ALREADY_OFFLINE > "$dest/stop.txt"
        echo 0 > "$dest/stop-exit.txt"
    fi
    cat "$node/state" > "$dest/slpi-final-state.txt"
    if [ "$(cat "$node/state")" = offline ]; then
        timeout -s TERM -k 2 5 sh -c 'echo 0 > "$1"' sh "$power" > "$dest/power-off.txt" 2>&1
        printf '%s\\n' "$?" > "$dest/power-off-exit.txt"
    else
        echo RETAINED_REFS_DSP_NOT_OFFLINE > "$dest/power-off.txt"
        echo NOT_ATTEMPTED > "$dest/power-off-exit.txt"
    fi
    cat "$power" > "$dest/power-final.txt"
    cat /sys/kernel/debug/regulator/regulator_summary > "$dest/regulators-final.txt"
    cat /proc/uptime /proc/sys/kernel/tainted > "$dest/kernel-state-after.txt"
    sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-after.txt"
    sha256sum -c "$src/sources-before.sha256" > "$dest/source-after.txt"
    (cd "$root" && find . -type f -exec sha256sum '{}' ';') > "$dest/ram-tree-after.sha256"
    dmesg > "$dest/dmesg-final.txt"
    printf '%s\\n' "$code" > "$dest/trial-exit.txt"
    (cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
    tar -C "$dest" -cf /tmp/k113-sensor-ram-v5.tar .
    sha256sum /tmp/k113-sensor-ram-v5.tar
    printf 'RAM_V5_FINAL_SLPI=%s POWER=%s TAINT=%s\\n' "$(cat "$node/state")" "$(cat "$power")" "$(cat /proc/sys/kernel/tainted)"
    exit "$code"
}
trap finish EXIT
modules=/var/lib/samurai/k113-modules-candidate
(cd "$modules" && sha256sum -c SHA256SUMS) > "$dest/module-check.txt"
''')
anchor = 'cat "$node/recovery" > "$dest/recovery-before.txt"\n'
assert text.count(anchor) == 1
text = text.replace(anchor, '''echo 1 > "$power"
test "$(cat "$power")" = 'vdd=1 vddio=1'
cat "$power" > "$dest/power-enabled.txt"
cat /sys/kernel/debug/regulator/regulator_summary > "$dest/regulators-enabled.txt"
''' + anchor)
start = text.index('if [ "$started" != 0 ]')
end = text.index('\nsleep 5',start)
text = text[:start] + '''if [ "$started" != 0 ] || [ "$(cat "$node/state")" != running ]; then
    echo QUERY_NOT_RUN_START_FAILED > "$dest/result.txt"
    exit 1
fi
''' + text[end:]
start = text.index("set +e\ntimeout -s TERM -k 2 12 sh -c 'echo stop")
text = text[:start] + '''printf 'SENSOR_QUERY_EXIT=%s RPCD_EXIT=%s\\n' "$query" "$daemon"
exit 0
'''
(ref / 'kernel113/test-sensor-ram-v5.sh').write_text(text)
print('KERNEL113_SINGLE_START_RAM_V5_WITH_OFFLINE_ONLY_SUPPLY_CLEANUP_PREPARED')
