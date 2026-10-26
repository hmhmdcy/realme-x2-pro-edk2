from pathlib import Path
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel126'
s=(ref/'collect-preflash.sh').read_text().replace("'^#118 '","'^#126 '").replace('k119-first-runtime','k126-first-runtime').replace('k126-preflash','k126-firmware-preflash').replace('7.3.0-rc6-rmx1931-samurai+','7.3.0-rc6-rmx1931-samurai-k126+').replace('test "$(pgrep -x phosh)" = 3492','test -n "$(pgrep -x phosh)"').replace('test "$(pgrep -x phoc)" = 3190','test -n "$(pgrep -x phoc)"').replace('CURRENT118','CURRENT126')
s=s.replace('pgrep -x phosh >', '''cp /var/lib/samurai/k126-preflash/new-release.txt "$dest/new-release.txt"
cp /var/lib/samurai/k126-preflash/new-module-tree.sha256 "$dest/new-module-tree.sha256"
(cd /usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k126+ && sha256sum -c "$dest/new-module-tree.sha256") > "$dest/new-module-check.txt"
pgrep -x phosh >''')
(ref/'collect-firmware-preflash.sh').write_text(s)
for original,new in [('quiesce-current118.sh','quiesce-firmware-current126.sh'),('freeze-for-bootloader.sh','freeze-firmware-for-bootloader.sh')]:
 s=(ref/original).read_text().replace("'^#118 '","'^#126 '").replace('k126-preflash','k126-firmware-preflash').replace('k126-quiesce','k126-firmware-quiesce').replace('CURRENT118','CURRENT126')
 if original.startswith('quiesce'):
  s=s.replace('dmesg > "$dest/dmesg-before.txt"', '''dmesg > "$dest/dmesg-before.txt"
if test -d /sys/module/qcom_camss; then
 test ! -e /dev/media0
 rmmod qcom_camss
fi
test ! -d /sys/module/qcom_camss''')
 (ref/new).write_text(s)
s=(ref/'verify-quiesce.py').read_text().replace("out/'quiesce-private.tar'","out/'firmware-quiesce-private.tar'").replace("out/'source-boot-id-private.txt'","out/'current-boot-id-private.txt'").replace('current_kernel=118','current_kernel=126').replace('quiesce-validation.json','firmware-quiesce-validation.json').replace('CURRENT118','CURRENT126')
(ref/'verify-firmware-quiesce.py').write_text(s)
s=(ref/'enter-bootloader.ps1').read_text().replace("$Prefix='tpg-first'","$Prefix='embedded-tpg'").replace('source-boot-id-private.txt','current-boot-id-private.txt').replace('quiesce-validation.json','firmware-quiesce-validation.json').replace('k126-freeze-for-bootloader.sh','k126-freeze-firmware-for-bootloader.sh').replace('Current118','Current126')
(ref/'enter-firmware-bootloader.ps1').write_text(s)
print('K126_CURRENT126_FRESH_FIRMWARE_GUARDS_PREPARED')
