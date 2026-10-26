"""Read only the current runtime's upgrade integration indicators."""
from pathlib import Path
import json
import host

code = '''from pathlib import Path
import json
args=Path('/proc/cmdline').read_text().split()
print(json.dumps(dict(
 bringup_flags={x:x in args for x in ['clk_ignore_unused','pd_ignore_unused','regulator_ignore_unused']},
 boot_directory_entries=len(list(Path('/boot').iterdir())),
 mkinitfs_deviceinfo_present=Path('/etc/deviceinfo').exists(),
 camera_config_cpu='mode: cpu' in Path('/etc/libcamera/configuration.yaml').read_text(),
 kernel_release=Path('/proc/sys/kernel/osrelease').read_text().strip()
)))
'''
q = host.ssh('python3 -', input=code.encode(), timeout=20)
d = json.loads(q.stdout)
Path(__file__).with_name('runtime-layering-validation.json').write_text(json.dumps(d, indent=2) + '\n')
print(json.dumps(d, indent=2))
