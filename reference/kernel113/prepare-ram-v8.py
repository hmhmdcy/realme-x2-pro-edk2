from pathlib import Path
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
text=(ref/'test-sensor-ram-v7.sh').read_text()
text=text.replace('k113-reboot-radio-clean-2/','k113-reboot-radio-clean-3/')
text=text.replace('ram-v7','ram-v8').replace('RAM_V7','RAM_V8')
assert text.count('owner=$!\nsleep 10')==1
text=text.replace('owner=$!\nsleep 10','owner=$!\nsleep 60')
text=text.replace('timeout -s TERM -k 3 90 ','timeout -s TERM -k 3 150 ')
anchor='fi\nwait "$owner"'
assert text.count(anchor)==1
text=text.replace(anchor,'''fi
for kind in light proximity magnetometer; do
    if ! kill -0 "$owner" 2>/dev/null; then break; fi
    timeout -s TERM -k 2 18 ssccli --debug --sensor "$kind" --timeout 10 > "$dest/$kind.txt" 2>&1
    printf '%s\\n' "$?" > "$dest/$kind-exit.txt"
done
wait "$owner"''')
(ref/'test-sensor-ram-v8.sh').write_text(text)
print('KERNEL113_RAM_V8_LATE_ACCEL_LIGHT_PROXIMITY_MAG_QUERIES_PREPARED')
