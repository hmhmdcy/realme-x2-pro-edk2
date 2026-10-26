from pathlib import Path
import shutil, subprocess
root=Path('/mnt/e/RealmeX2Pro edk2')
ref=root/'reference/kernel101'
out=Path('/mnt/e/edk2-samurai-out/kernel101')
assert not (ref/'collect-preflash.sh').exists()
for name in ('reboot-f1.ps1','read-eud.ps1','scp-private.ps1','receive-backups.ps1','split-backups.sh'):
    text=(root/'reference/kernel100'/name).read_text().replace('kernel100','kernel101').replace('K100','K101').replace('k100','k101').replace('#98 SMP PREEMPT','#99 SMP PREEMPT')
    (ref/name).write_text(text)
text=(root/'reference/kernel100/collect-preflash.sh').read_text().replace('k100','k101').replace('#98 SMP PREEMPT','#99 SMP PREEMPT').replace('c325eb6421b1194c17e309143183e0cf97192a395d7f4e537e829047ae6abea9','02554a24fa661c00f2684f8cc1aee3ae57b5887c552bb335d372e8276fbdb9ea')
text=text.replace('dmesg > "$dir/dmesg.txt"','mountpoint -q /sys/kernel/debug || mount -t debugfs debugfs /sys/kernel/debug\ndmesg > "$dir/dmesg.txt"')
(ref/'collect-preflash.sh').write_text(text)
(ref/'stop-connectivity.sh').write_text((root/'reference/kernel100/stop-connectivity.sh').read_text())
text=(root/'reference/kernel99/build-firmware.sh').read_text().replace('kernel99','kernel101').replace('k99-haptics','k101-adsp').replace('dtb-haptics','dtb-adsp')
(ref/'build-firmware.sh').write_text(text)
text=(root/'reference/kernel99/verify-firmware.py').read_text().replace('kernel99','kernel101').replace('k99-haptics','k101-adsp').replace("dt_audit['cpio_byte_identical']","dt_audit['original_initramfs_files_preserved']").replace('haptics_bus_and_node_only','adsp_and_apr_core_only')
(ref/'verify-firmware.py').write_text(text)
text=(root/'reference/kernel99/flash-haptics.ps1').read_text().replace('kernel99','kernel101').replace('K99','K101').replace('k99','k101').replace('haptics.img','adsp.img').replace(' -or !$audit.cpio_byte_identical','').replace('$audit.kernel_build -ne 98','$audit.kernel_build -ne 100')
(ref/'flash-adsp.ps1').write_text(text)
shutil.copyfile(out.parent/'kernel100/fastboot-identity.json',out/'fastboot-identity.json')
for p in ref.glob('*.sh'):subprocess.run(['sh','-n',str(p)],check=True)
print('ADSP_TOOLS_PREPARED')
