from pathlib import Path
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
text=(ref/'test-sensor-ram-v9.sh').read_text()
text=text.replace('k113-reboot-radio-clean-4/','k113-reboot-audio-clean-6/')
text=text.replace('ram-v9','ram-v10').replace('RAM_V9','RAM_V10')
text=text.replace('timeout -s TERM -k 3 240 ', 'timeout -s TERM -k 3 180 ')
text=text.replace('PROXIMITY_COVER_WINDOW_OPEN_120_SECONDS','PROXIMITY_AUTOMATIC_SAMPLE_OPEN_10_SECONDS')
text=text.replace('PROXIMITY_COVER_WINDOW_CLOSED','PROXIMITY_AUTOMATIC_SAMPLE_CLOSED')
text=text.replace('timeout -s TERM -k 2 128 ssccli --debug --sensor proximity --timeout 120','timeout -s TERM -k 2 18 ssccli --debug --sensor proximity --timeout 10')
start=text.index('wait "$owner"\ndaemon=$?\ncat /proc/uptime')
end=text.index('test "$(cat "$node/state")" = running',start)
text=text[:start]+'''set -e
printf '%s\\n' "$query" > "$dest/query-exit.txt"
cat "$node/state" > "$dest/slpi-state-after.txt"
dmesg > "$dest/dmesg-after.txt"
qrtr-lookup > "$dest/qrtr-after.txt"
printf 'COREDUMP_PRE_GUARD_SNAPSHOT\\n'
printf '%s\\n' "$node" > "$dest/coredump-guard-node.txt"
cat "$node/state" > "$dest/coredump-guard-state.txt"
cat "$node/recovery" > "$dest/coredump-guard-recovery.txt"
find /sys/class/devcoredump -maxdepth 1 -name 'devcd*' -print > "$dest/coredump-guard-existing.txt"
''' +text[end:]
anchor="printf 'SLPI_COREDUMP_CAPTURE_FINISHED\\n'"
text=text.replace(anchor,anchor+'''
set +e
if kill -0 "$owner" 2>/dev/null; then kill -TERM "$owner"; fi
wait "$owner"
daemon=$?
owner=
cat /proc/uptime > "$dest/daemon-uptime-end.txt"
printf '%s\\n' "$daemon" > "$dest/daemon-exit.txt"
set -e
''')
# Finalizer also records daemon status when a capture precondition fails.
text=text.replace('        wait "$owner"\n    fi', '''        wait "$owner"
        printf '%s\\n' "$?" > "$dest/daemon-exit.txt"
        cat /proc/uptime > "$dest/daemon-uptime-end.txt"
    fi''',1)
(ref/'test-sensor-ram-v10.sh').write_text(text)
print('RAM_V10_CAPTURE_WITH_ACTIVE_LISTENER_AND_EXPLICIT_PRECONDITION_SNAPSHOTS_PREPARED')
