from pathlib import Path

ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel74')
text = (ref/'flash-handoff.ps1').read_text().replace('handoff','detach').replace(
    '25db108b8a19f2d3e1cb695438ee134a1c8e9a04d1db6b57601130aa9cde9e5a',
    '90c2cc26f43fc0194d46db66c5eb1270f1accbfd777c52207f7547281024d52f')
needle = "$devices=Invoke-K72Fastboot 'detach-confirm-devices' @('devices') 15\n"
assert text.count(needle)==1
text = text.replace(needle,'''$devices=''
for ($attempt=1; $attempt -le 10; $attempt++) {
    $devices=Invoke-K72Fastboot "detach-confirm-devices-$attempt" @('devices') 15
    if ($devices -match '(?im)^62bc28a1\\s+fastboot\\s*$') {break}
    Start-Sleep -Milliseconds 1000
}
''')
(ref/'flash-detach.ps1').write_text(text)
text = (ref/'reboot-fastboot.ps1').read_text()
needle = "$devices=Invoke-RebootFastboot 'devices' @('devices')\n"
assert text.count(needle)==1
text = text.replace(needle,'''$devices=''
for ($attempt=1; $attempt -le 10; $attempt++) {
    $devices=Invoke-RebootFastboot "devices-$attempt" @('devices')
    if ($devices -match '(?im)^62bc28a1\\s+fastboot\\s*$') {break}
    Start-Sleep -Milliseconds 1000
}
''')
(ref/'reboot-ready-fastboot.ps1').write_text(text)
print('Added a bounded enumeration wait; F1 still has one OUT attempt, and writes remain logdump-only.')
