from pathlib import Path

ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
# Preserve the prepared C35 comparison as the next fresh-boot trial.
c35=(ref/'test-sensor-ram-v15.sh').read_text()
assert 'samurai-c35-trial' in c35 and 'k113-reboot-audio-clean-11/' in c35
assert not (ref/'test-sensor-ram-v16.sh').exists()
(ref/'test-sensor-ram-v16.sh').write_text(c35.replace('ram-v15','ram-v16').replace('RAM_V15','RAM_V16').replace('k113-reboot-audio-clean-11/','k113-reboot-audio-clean-12/'))

text=(ref/'test-sensor-ram-v14.sh').read_text()
text=text.replace('ram-v14','ram-v15').replace('RAM_V14','RAM_V15')
text=text.replace('k113-reboot-audio-clean-10/','k113-reboot-audio-clean-11/')
assert '75 ssccli' in text and '--timeout 60' in text and '180 /var/lib/samurai' in text
text=text.replace('75 ssccli','195 ssccli').replace('--timeout 60','--timeout 180')
text=text.replace('180 /var/lib/samurai','300 /var/lib/samurai')
(ref/'test-sensor-ram-v15.sh').write_text(text)
print('V15_SAME_C28_MAGNETOMETER_180_SECOND_WINDOW; C35_COMPARISON_PRESERVED_AS_V16_BOOT12')
