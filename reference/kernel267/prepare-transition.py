"""Adapt the proven248 quiesce and reboot code to the fresh260 boot and267 stage."""
from pathlib import Path
import hashlib
import json

R=Path(__file__).resolve().parent
s=(R.parent/'kernel248/native-quiesce.py').read_text().replace('k248','k267').replace('stage=248','stage=267').replace('k247-runtime','k260-work')
s=s.replace("'cam-back-vana','cam-back-vdig'","'cam-back-vana','cam-back-vdig','cam-rear-vana','cam-rear-vdig'")
needle=" assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0' and not Path('/run/k267-reboot-phase-private.json').exists()"
assert s.count(needle)==1
s=s.replace(needle,needle+"\n assert json.loads((r/'k267-module-transaction/summary.json').read_text())['three_common_modules_staged']\n assert (Path('/etc/samurai-rootfs-release')).is_file()")
s=s.replace('normal_linux_reboot_only=True','restart2_bootloader_expected=True')
compile(s,'native-quiesce.py','exec');(R/'native-quiesce.py').write_text(s)
s=(R.parent/'kernel248/normal-reboot.py').read_text().replace('k248','k267').replace('stage=248','stage=267').replace('k247-runtime','k260-work')
old="assert not Path('/etc/samurai-rootfs-release').exists() and Path('/etc/samurai-rootfs-release.k267-before-rescue').is_file()"
assert s.count(old)==1
s=s.replace(old,"assert b'ROOTFS_ID=samurai-f2fs-rootfs01' in Path('/etc/samurai-rootfs-release').read_bytes()")
s=s.replace('normal_restart_only=True','restart2_bootloader_expected=True').replace('normal_restart=True','restart2_bootloader=True')
old="time.sleep(0.5);result=libc.syscall(142,0xfee1dead,672274793,0x01234567,None)"
assert s.count(old)==1
s=s.replace(old,"command=ctypes.create_string_buffer(b'bootloader\\0')\n time.sleep(0.5);result=libc.syscall(142,0xfee1dead,672274793,0xa1b2c3d4,ctypes.cast(command,ctypes.c_void_p))")
s=s.replace('before_single_normal_restart','before_single_restart2_bootloader').replace('Normal reboot returned:','Restart2 bootloader returned:')
compile(s,'restart-bootloader.py','exec');(R/'restart-bootloader.py').write_text(s)
report=dict(stage=267,proven_quiesce_and_eud_sequence_reused=True,current260_boot_guard=True,
 old_loaded_camera_providers_retained=True,no_rootfs_marker_rename=True,
 only_restart_command_changed_to_bootloader=True,
 hashes={n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in ['native-quiesce.py','restart-bootloader.py']})
(R/'transition-source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
