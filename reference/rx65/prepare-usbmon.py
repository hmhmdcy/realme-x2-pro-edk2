from pathlib import Path
import hashlib
import json
import subprocess
import usb
import usb.backend.libusb1

root=Path('/mnt/e/edk2-samurai-out/rx65')
out=root/'wsl-readiness.json'
assert not out.exists(), 'Preserve consumed readiness record.'
mounted=subprocess.run(['findmnt','-n','-t','debugfs','--target','/sys/kernel/debug'],capture_output=True,text=True)
if mounted.returncode:
    subprocess.run(['mount','-t','debugfs','debugfs','/sys/kernel/debug'],check=True)
subprocess.run(['modprobe','usbmon'],check=True)
assert Path('/sys/kernel/debug/usb/usbmon/0u').exists()
backend=Path(usb.backend.libusb1.__file__)
state={'kernel':subprocess.run(['uname','-r'],check=True,capture_output=True,text=True).stdout.strip(),
       'pyusb':usb.__version__,'libusb_backend_sha256':hashlib.sha256(backend.read_bytes()).hexdigest(),
       'usbmon_ready':True,'windows_candidate_loaded':False,'serial_opened':False}
out.write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(state))
