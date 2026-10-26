from pathlib import Path
import json,subprocess
out=Path('/mnt/e/edk2-samurai-out/rx65/wsl-compressed-readiness.json')
mounted=subprocess.run(['findmnt','-n','-t','debugfs','--target','/sys/kernel/debug'],capture_output=True,text=True)
if mounted.returncode:subprocess.run(['mount','-t','debugfs','debugfs','/sys/kernel/debug'],check=True)
subprocess.run(['modprobe','usbmon'],check=True)
assert Path('/sys/kernel/debug/usb/usbmon/0u').exists()
if not out.exists():out.write_text(json.dumps({'usbmon_ready':True,'immutable_snapshot_only':True})+'\n')
