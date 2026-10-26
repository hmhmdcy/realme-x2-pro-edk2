from pathlib import Path

root=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel75')
s=(root/'flash-no-eot.ps1').read_text()
needle="if (!@($events | Where-Object {$_.event -eq 'receipt' -and $_.text -eq 'F1'}).Count) {throw 'No current F1 receipt'}"
assert s.count(needle)==1
s=s.replace(needle,"""# USB disconnected before the F1 receipt reached the host. Do not fabricate
# an ACK or resend the command. A completed single OUT plus this script's
# independent serial/product/partition fastboot checks authorizes the write.
if (@($events | Where-Object {$_.event -eq 'out_submit'}).Count -ne 1 -or
    !@($events | Where-Object {$_.event -eq 'out_complete' -and $_.length -eq 2}).Count) {
    throw 'No completed one-shot bootloader request'
}""")
for suffix in ('confirm-devices-','confirm-product','confirm-size-logdump','flash-logdump','reboot','flash-validation.json'):
    s=s.replace('no-eot-'+suffix,'no-eot-ready-'+suffix)
s=s.replace('boot_written=$false;',"f1_receipt_observed=$false;independent_fastboot_confirmed=$true;boot_written=$false;")
(root/'flash-no-eot-ready.ps1').write_text(s)
print('Prepared independent-fastboot fallback; EUD request is not resent')
