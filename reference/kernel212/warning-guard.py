from pathlib import Path
import subprocess
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k211-runtime/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='512'
warning_log=subprocess.check_output(['dmesg'])
known_warnings=[line for line in warning_log.splitlines() if b'WARNING:' in line]
archived_log=Path('/var/lib/samurai/k211-user-libcamera-system/dmesg-after-private.txt').read_bytes()
archived_warnings=[line for line in archived_log.splitlines() if b'WARNING:' in line]
assert len(archived_warnings)==349
assert all(b'__arm_lpae_unmap' in line and b'drivers/iommu/io-pgtable-arm.c:673' in line for line in archived_warnings)
# The printk ring has wrapped; compare complete timestamped lines to the saved evidence.
assert set(known_warnings).issubset(set(archived_warnings))
assert all(warning_log.count(term)==0 for term in [b'Oops:',b'gpu fault:',b'fatal error received',b'Frame reassembly failed'])
