from pathlib import Path
import hashlib
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
out=Path('/mnt/e/edk2-samurai-out/kernel113')
text=(ref/'test-sensor-ram-v5.sh').read_text()
text=text.replace('k113-first-before-slpi/','k113-reboot-radio-clean-1/').replace('ram-v5','ram-v6').replace('RAM_V5','RAM_V6')
text=text.replace('/var/lib/samurai/k112-rpcd-ram-trial/hexagonrpcd-v3','/var/lib/samurai/k113-tools/hexagonrpcd-v4')
digest=hashlib.sha256((out/'hexagonrpcd-ram-trial-v4').read_bytes()).hexdigest()
anchor='timeout -s TERM -k 3 60 /var/lib/samurai/k113-tools/hexagonrpcd-v4'
assert text.count(anchor)==1
text=text.replace(anchor,f'''echo '{digest}  /var/lib/samurai/k113-tools/hexagonrpcd-v4' | sha256sum -c - > "$dest/daemon-check.txt"
cat /proc/uptime > "$dest/daemon-uptime-start.txt"
''' + anchor)
text=text.replace('daemon=$?\nowner=', 'daemon=$?\ncat /proc/uptime > "$dest/daemon-uptime-end.txt"\nowner=')
(ref/'test-sensor-ram-v6.sh').write_text(text)
print('KERNEL113_FRESH_BOOT_RAM_V6_DIAGNOSTIC_DAEMON_GUARDED')
