from pathlib import Path

ref = Path('/mnt/e/RealmeX2Pro edk2/reference')
target = ref/'kernel99/flash-haptics.ps1'
assert not target.exists()
s = (ref/'kernel98/flash-connectivity.ps1').read_text().replace('kernel98','kernel99').replace('K98','K99').replace('k98','k99')
old = 'if (!$audit.candidate_audit_pass -or !$audit.original_initramfs_files_preserved -or !$audit.earlier_snapshots_preserved -or !$audit.dtb_byte_identical -or !$audit.firmware_boot_reused_byte_identical -or $audit.embedded_wifi_credentials -or $audit.embedded_device_addresses -or $audit.nv_partition_writes -or $audit.kernel_build -ne 97)'
new = 'if (!$audit.candidate_audit_pass -or !$audit.original_initramfs_files_preserved -or !$audit.earlier_snapshots_preserved -or !$audit.firmware_dtb_raw_section_matches -or !$audit.other_executable_bytes_unchanged -or !$audit.cpio_byte_identical -or $audit.embedded_wifi_credentials -or $audit.embedded_device_addresses -or $audit.nv_partition_writes -or $audit.kernel_build -ne 98)'
assert s.count(old)==1
s=s.replace(old,new).replace("-ne 'logdump'", "-ne 'boot,logdump'").replace('logdump-k99-connectivity.img','logdump-k99-haptics.img')
insertion = '''$bootSize=Invoke-K99Fastboot 'confirm-size-boot' @('-s',$k99serial,'getvar','partition-size:boot') 15
if ($bootSize -notmatch 'partition-size:boot:\\s*(0x[0-9a-fA-F]+)') {throw 'Boot partition size missing'}
if ([Convert]::ToInt64($Matches[1].Substring(2),16) -ne 100663296) {throw 'Boot partition size mismatch'}
$bootImage="$k99out\\boot-k99-haptics.img"
if ((Get-Item $bootImage).Length -ne $audit.boot_bytes -or (Get-Item $bootImage).Length -gt 100663296 -or (Get-FileHash $bootImage).Hash.ToLowerInvariant() -ne $audit.boot_sha256) {throw 'Firmware boot size/hash mismatch'}
'''
anchor="$result=Invoke-K99Fastboot 'flash-logdump'"
assert s.count(anchor)==1
s=s.replace(anchor,insertion+'''$bootResult=Invoke-K99Fastboot 'flash-boot' @('-s',$k99serial,'flash','boot',$bootImage) 60
if ($bootResult -notmatch "Writing 'boot'\\s+OKAY") {throw 'Successful boot write not observed'}
$bootResult
'''+anchor)
s=s.replace("flashed_partitions=@('logdump');boot_reused=$true", "flashed_partitions=@('boot','logdump');firmware_dtb_rebuilt=$true")
target.write_text(s)
print('HAPTICS_FLASH_SCRIPT_PREPARED')
