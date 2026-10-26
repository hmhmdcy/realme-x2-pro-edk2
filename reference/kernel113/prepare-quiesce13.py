from pathlib import Path
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
text=(ref/'quiesce-clean-boot12.sh').read_text()
assert 'k113-reboot-audio-clean-12/' in text
text=text.replace('k113-reboot-audio-clean-12/','k113-reboot-audio-clean-13/')
old="timeout -s TERM -k 2 15 sh -c 'echo stop > \"$1/state\"' sh \"$adsp\""
assert text.count(old)==1
text=text.replace(old,"# boot12 native stop completed at ~15.07s; leave bounded margin.\n"+old.replace('-k 2 15','-k 2 25'))
anchor='cat "$adsp/state" > "$dest/adsp-final-state.txt"\n'
assert text.count(anchor)==1
text=text.replace(anchor,anchor+'''cat /proc/asound/cards > "$dest/soundcards-after-stop.txt"
test "$(cat "$dest/soundcards-after-stop.txt")" = '--- no soundcards ---'
test ! -e /proc/asound/card0
test ! -e /proc/asound/card0/pcm0p/sub0/status
test ! -e /proc/asound/card0/pcm1c/sub0/status
echo CARD0_AND_PLAYBACK_CAPTURE_STATUS_NODES_ABSENT_AFTER_NATIVE_ADSP_STOP > "$dest/post-stop-audio-card-absent.txt"
for number in 0 1 2; do
    item=/sys/class/remoteproc/remoteproc$number
    test "$(cat "$item/state")" = offline
    printf '%s %s %s\\n' "$number" "$(cat "$item/name")" "$(cat "$item/state")"
done > "$dest/remoteproc-final-state.txt"
cat /sys/devices/platform/sensor-power/state > "$dest/sensor-power-final-state.txt"
test "$(cat "$dest/sensor-power-final-state.txt")" = 'vdd=0 vddio=0'
cat /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status > "$dest/amps-final.txt"
test "$(grep -c 'powered=0 muted=1' "$dest/amps-final.txt")" = 2
test -z "$(pgrep -u 10000 || true)"
test -z "$(pidof wpa_supplicant || true)"
''')
(ref/'quiesce-clean-boot13.sh').write_text(text)
print('BOOT13_QUIESCE_PREPARED_ADSP_STOP_DEADLINE_25_SECONDS')
