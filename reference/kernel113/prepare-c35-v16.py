from pathlib import Path

ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
path=ref/'test-sensor-ram-v16.sh'
text=path.read_text()
assert 'samurai-c35-trial' in text and 'k113-reboot-audio-clean-12/' in text
assert text.count('for kind in light magnetometer; do')==1
path.write_text(text.replace('for kind in light magnetometer; do','for kind in light magnetometer gyroscope compass; do'))
clean=(ref/'quiesce-clean-boot10.sh').read_text()
assert 'k113-reboot-audio-clean-10/' in clean
(ref/'quiesce-clean-boot11.sh').write_text(clean.replace('k113-reboot-audio-clean-10/','k113-reboot-audio-clean-11/'))
print('C35_V16_FRESH_BOOT12_WITH_GYROSCOPE_AND_COMPASS_QUERIES_PREPARED')
