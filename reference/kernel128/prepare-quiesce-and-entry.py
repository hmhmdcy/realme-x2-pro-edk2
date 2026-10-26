from pathlib import Path
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel128';old=r/'reference/kernel126'
s=(old/'quiesce-firmware-current126.sh').read_text().replace('k126-firmware-preflash','k128-preflash').replace('k126-firmware-quiesce','k128-quiesce').replace('7.3.0-rc6-rmx1931-samurai-k126+','7.3.0-rc6-rmx1931-samurai-k128+').replace('k126-firmware-quiesce-private.tar','k128-quiesce-private.tar').replace('K126_CURRENT126','K128_CURRENT126')
s=s.replace(' test ! -e /dev/media0\n rmmod qcom_camss',' test "$(cat /sys/module/qcom_camss/parameters/dma_trace)" = N\n rmmod qcom_camss\n test ! -e /dev/media0')
s=s.replace('dmesg > "$dest/dmesg-before.txt"','''dmesg > "$dest/dmesg-before.txt"
for name in display radio; do
 path=/sys/kernel/tracing/instances/$name
 echo 0 > "$path/tracing_on"
 timeout -k 2 10 cat "$path/trace" > "$dest/$name-trace-private.txt"
 test "$(cat "$path/tracing_on")" = 0
done''')
assert "'^#126 '" in s and 'k128-preflash' in s and 'k128-quiesce' in s and '7.3.0-rc6-rmx1931-samurai-k128+' in s
(ref/'quiesce-current126.sh').write_text(s)
s=(old/'freeze-firmware-for-bootloader.sh').read_text().replace('k126-firmware-preflash','k128-preflash').replace('k126-firmware-quiesce','k128-quiesce').replace('7.3.0-rc6-rmx1931-samurai-k126+','7.3.0-rc6-rmx1931-samurai-k128+').replace('/run/k126-','/run/k128-').replace('K126_F2FS','K128_F2FS')
(ref/'freeze-for-bootloader.sh').write_text(s)
s=(old/'enter-bootloader.ps1').read_text().replace("$Prefix='tpg-first'","$Prefix='key-delete-first'").replace('kernel126','kernel128').replace('k126-freeze-for-bootloader.sh','k128-freeze-for-bootloader.sh').replace('K126_F2FS','K128_F2FS').replace('K126_CONTROLLED_THAW','K128_CONTROLLED_THAW')
(ref/'enter-bootloader.ps1').write_text(s)
s=(old/'verify-quiesce.py').read_text().replace('kernel126','kernel128').replace('current_kernel=118,target_kernel=126','current_kernel=126,target_kernel=128').replace('staged126_module_checks_pass','staged128_module_checks_pass').replace('K126_CURRENT118','K128_CURRENT126')
(ref/'verify-quiesce.py').write_text(s)
print('K128_FRESH_CURRENT126_QUIESCE_FREEZE_ENTRY_TOOLS_PREPARED',flush=True)
