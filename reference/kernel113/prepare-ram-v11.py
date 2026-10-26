from pathlib import Path
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
text=(ref/'test-sensor-ram-v10.sh').read_text()
text=text.replace('k113-reboot-audio-clean-6/','k113-reboot-audio-clean-7/')
text=text.replace('ram-v10','ram-v11').replace('RAM_V10','RAM_V11')
anchor='test -z "$(find /sys/class/devcoredump -maxdepth 1 -name \'devcd*\' -print)"'
assert text.count(anchor)==1
text=text.replace(anchor,'''slpi_dump_node() {
    for candidate in /sys/class/devcoredump/devcd*; do
        test -e "$candidate" || continue
        if [ "$(readlink -f "$candidate/failing_device")" = "$(readlink -f "$node")" ]; then
            printf '%s\\n' "$candidate"
        fi
    done
}
test -z "$(slpi_dump_node)"''')
text=text.replace('while [ -z "$(find /sys/class/devcoredump -maxdepth 1 -name \'devcd*\' -print)" ]', 'while [ -z "$(slpi_dump_node)" ]')
text=text.replace("dump_node=$(find /sys/class/devcoredump -maxdepth 1 -name 'devcd*' -print)", 'dump_node=$(slpi_dump_node)')
(ref/'test-sensor-ram-v11.sh').write_text(text)
clean=(ref/'quiesce-audio-radio.sh').read_text()
clean=clean.replace('k113-slow-boot-radio-clean-5/','k113-reboot-audio-clean-6/').replace(')" = 512', ')" = 0')
clean=clean.replace("dmesg | grep -q 'WARNING: sound/soc/codecs/wcd934x.c:1457'\n",'')
clean=clean.replace("test \"$(dmesg | grep -c 'WARNING:')\" = 1\n",'')
(ref/'quiesce-clean-boot6.sh').write_text(clean)
print('V11_ONLY_SLPI_COREDUMP_SELECTOR_AND_FRESH_BOOT6_AUDIO_QUIESCE_PREPARED')
