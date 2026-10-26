from pathlib import Path
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
text=(ref/'test-sensor-ram-v13.sh').read_text()
text=text.replace('k113-reboot-audio-clean-9/','k113-reboot-audio-clean-10/')
text=text.replace('ram-v13','ram-v14').replace('RAM_V13','RAM_V14')
anchor='    timeout -s TERM -k 2 18 ssccli --debug --sensor "$kind" --timeout 10 > "$dest/$kind.txt" 2>&1'
assert text.count(anchor)==1
text=text.replace(anchor,'''    if [ "$kind" = magnetometer ]; then
        cat /proc/uptime > "$dest/magnetometer-window-uptime.txt"
        printf 'MAGNETOMETER_PHYSICAL_ROTATION_WINDOW_OPEN_60_SECONDS\\n'
        timeout -s TERM -k 2 75 ssccli --debug --sensor "$kind" --timeout 60 > "$dest/$kind.txt" 2>&1
    else
        timeout -s TERM -k 2 18 ssccli --debug --sensor "$kind" --timeout 10 > "$dest/$kind.txt" 2>&1
    fi''')
anchor='    printf \'%s\\n\' "$?" > "$dest/$kind-exit.txt"'
assert text.count(anchor)==1
text=text.replace(anchor,anchor+'''\n    if [ "$kind" = magnetometer ]; then printf 'MAGNETOMETER_PHYSICAL_ROTATION_WINDOW_CLOSED\\n'; fi''')
(ref/'test-sensor-ram-v14.sh').write_text(text)
clean=(ref/'quiesce-clean-boot8.sh').read_text().replace('k113-reboot-audio-clean-8/','k113-reboot-audio-clean-9/')
(ref/'quiesce-clean-boot9.sh').write_text(clean)
print('C28_REPEAT_MAGNETOMETER_ROTATION_TRIAL_FOR_BOOT10_PREPARED')
