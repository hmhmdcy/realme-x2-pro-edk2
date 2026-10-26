from pathlib import Path

root = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel112')
text = (root / 'test-sensor-ram-v3.sh').read_text()
assert text.count('k112-reboot-radio-clean-1/') == 1
text = text.replace('k112-reboot-radio-clean-1/', 'k112-reboot-radio-clean-2/')
assert text.count('hexagonrpcd-v2') == 1
text = text.replace('hexagonrpcd-v2', 'hexagonrpcd-v3')
assert text.count('owner=$!\nsleep 3') == 1
text = text.replace('owner=$!\nsleep 3', 'owner=$!\nsleep 10')
assert text.count('timeout -s TERM -k 3 35 ') == 1
text = text.replace('timeout -s TERM -k 3 35 ', 'timeout -s TERM -k 3 60 ')
text = text.replace('ram-v3', 'ram-v4')
(root / 'test-sensor-ram-v4.sh').write_text(text)
print('Fresh-boot RAM v4 trial prepared; daemon 60 seconds, sensor sampling 10 seconds')
