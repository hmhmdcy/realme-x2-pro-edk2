from pathlib import Path
import hashlib
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
out=Path('/mnt/e/edk2-samurai-out/kernel113')
text=(ref/'test-sensor-ram-v6.sh').read_text()
text=text.replace('k113-reboot-radio-clean-1/','k113-reboot-radio-clean-2/')
text=text.replace('ram-v6','ram-v7').replace('RAM_V6','RAM_V7').replace('hexagonrpcd-v4','hexagonrpcd-v5')
old='afa5fa18b1d013faaf09f48479b88235cf1015f61fe6248b6e04905c1f7aa64f'
assert text.count(old)==1
text=text.replace(old,hashlib.sha256((out/'hexagonrpcd-ram-trial-v5').read_bytes()).hexdigest())
text=text.replace('timeout -s TERM -k 3 60 ','timeout -s TERM -k 3 90 ')
anchor='query=$?\nwait "$owner"'
assert text.count(anchor)==1
text=text.replace(anchor,'''query=$?
if kill -0 "$owner" 2>/dev/null; then
    sleep 10
    timeout -s TERM -k 2 18 ssccli --debug --sensor accelerometer --timeout 10 > "$dest/accelerometer-late.txt" 2>&1
    printf '%s\\n' "$?" > "$dest/query-late-exit.txt"
fi
wait "$owner"''')
(ref/'test-sensor-ram-v7.sh').write_text(text)
print('KERNEL113_RAM_V7_EXTENDED_MID_RENAME_DAEMON_WITH_SECOND_QUERY_PREPARED')
