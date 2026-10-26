from pathlib import Path
r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel132'
prev = r / 'reference/kernel129'
text = (prev / 'flash-validated129.ps1').read_text().replace('kernel129', 'kernel132').replace('k129', 'k132').replace('K129', 'K132')
text = text.replace('console-node-first', 'charger-node-first').replace('console-node-r2', 'charger-node-first')
text = text.replace('$build.candidate -ne 129', '$build.candidate -ne 132')
text = text.replace('all_770_module_executable_sections_byte_equal128', 'all_770_module_executable_sections_byte_equal129')
text = text.replace('fixed_ipa_camss_cphy_cpas_preserved', 'charger_driver_unchanged')
text = text.replace('$boot.boot126_embedded_dtb_reused_byte_exact', '$boot.only_embedded_dtb_changed')
text = text.replace('$boot.dtb_byte_identical126', '$boot.fat_and_embedded_dtb_exactly_match_candidate')
text = text.replace("-ne 'logdump'", "-ne 'boot,logdump'")
text = text.replace('$before.current_kernel -ne 128', '$before.current_kernel -ne 129').replace('$before.target_kernel -ne 129', '$before.target_kernel -ne 132')
text = text.replace('Fresh128', 'Fresh129').replace('Current128', 'Current129')
text = text.replace('new129_directory', 'new132_directory').replace('old118_and126_and128', 'old118_and126_and129')
text = text.replace('logdump-k132-console-node.img', 'logdump-k132-charger.img')
needle = '@("$out\\modules-k132-private.tar.gz",$build.archive_sha256)'
assert needle in text
text = text.replace(needle, '@("$out\\boot-partition-k132-charger.img",$boot.boot_sha256),' + needle)
a = text.index('$image="$out\\logdump-k132-charger.img"')
b = text.index('$null=Invoke-CheckedFastboot', a)
text = text[:a] + '''foreach($item in @(@('boot',"$out\\boot-partition-k132-charger.img",[int64]100663296),@('logdump',"$out\\logdump-k132-charger.img",[int64]67108864))){
 $partition=$item[0];$image=$item[1]
 if((Get-Item -LiteralPath $image).Length -ne $item[2]){throw 'Image length changed'}
 $text=Invoke-CheckedFastboot "flash-$partition" @('-s',$serial,'flash',$partition,$image) 90
 if($text -notmatch ("Writing '"+$partition+"'\\s+OKAY") -or $text -match 'FAILED'){throw 'Flash completion unconfirmed; inspect actual state before proceeding'}
 Write-Output "K132_FLASH_${partition}_CONFIRMED"
}
''' + text[b:]
text = text.replace("partitions=@('logdump');boot_changed=$false", "partitions=@('boot','logdump');boot_changed=$true")
text = text.replace('K132_LOGDUMP_FLASH_AND_REBOOT_COMPLETE', 'K132_BOOT_LOGDUMP_FLASH_AND_REBOOT_COMPLETE')
text = text.replace('kernel_build=129', 'kernel_build=132')
(ref / 'flash-validated132.ps1').write_text(text)
for name in ['observe-current-fastboot.ps1', 'enable-eud.ps1', 'poll-new-boot.ps1', 'collect-runtime.sh', 'inspect-runtime.py']:
    text = (prev / name).read_text().replace('kernel129', 'kernel132').replace('k129', 'k132').replace('K129', 'K132')
    text = text.replace('console-node-r2', 'charger-node-first').replace('console-node-first', 'charger-node-first')
    text = text.replace("'^#129 '", "'^#132 '").replace('#129 SMP PREEMPT', '#132 SMP PREEMPT').replace('kernel_build=129', 'kernel_build=132')
    text = text.replace('embedded126_dtb_preserved=True', 'embedded132_dtb_with_charger_verified=True').replace('boot_bytes_match_embedded126=True', 'boot_bytes_match_embedded132=True')
    if name == 'collect-runtime.sh':
        text = text.replace('dmesg > "$dest/dmesg.txt"', '''test "$(readlink -f /sys/bus/i2c/devices/0-005c/driver)" = /sys/bus/i2c/drivers/mp2650
test -d /sys/class/power_supply/mp2650-input
cat /sys/class/power_supply/mp2650-input/uevent > "$dest/mp2650-uevent.txt"
stat -c '%a %n' /sys/class/power_supply/mp2650-input/online /sys/class/power_supply/mp2650-input/status /sys/class/power_supply/mp2650-input/voltage_now /sys/class/power_supply/mp2650-input/current_now > "$dest/mp2650-modes.txt"
(cd /usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k132+ && sha256sum -c /var/lib/samurai/k132-preflash/new-module-tree.sha256) > "$dest/full-module-check.txt"
rc-service bluetooth status > "$dest/bluez-service.txt"
dmesg > "$dest/dmesg.txt"''')
    if name == 'inspect-runtime.py':
        text = text.replace('report=dict(', '''node='/soc@0/geniqup@8c0000/i2c@884000/charger@5c'
assert live[node]['compatible']==b'mps,mp2650\\0' and live[node]['reg']==(0x5c).to_bytes(4,'big')
assert b'POWER_SUPPLY_ONLINE=1\\n' in data['mp2650-uevent.txt'] and b'POWER_SUPPLY_STATUS=' in data['mp2650-uevent.txt']
assert len(data['mp2650-modes.txt'].splitlines())==4 and all(l.startswith(b'444 ') for l in data['mp2650-modes.txt'].splitlines())
assert data['full-module-check.txt'].count(b': OK')>=770 and b'FAILED' not in data['full-module-check.txt']
assert b'started' in data['bluez-service.txt']
report=dict(persistent_mp2650_standard_power_supply_auto_registered=True,charger_attributes_read_only=True,all_matching_modules_verified=True,bluez_service_started=True,''')
    (ref / name).write_text(text)
print('K132_TWO_PARTITION_FLASHER_AND_AUTOREGISTERED_CHARGER_NATIVE_RUNTIME_TOOLS_READY')
