import host
code=r'''
from pathlib import Path
import json,subprocess
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k205-baseline/boot-id-private.txt').read_bytes()
out=root/'k205-uart-reprobe';failure=(out/'failure-private.txt').read_text().splitlines();errors={}
for p in sorted(out.glob('*private.log')):
 t=p.read_text(errors='replace')
 if 'error' in t.lower() or 'fail' in t.lower() or 'in use' in t.lower():errors[p.name]=dict(module_in_use='in use' in t.lower(),failed='failed' in t.lower(),lifecycle_busy='BT_LIFECYCLE_BUSY' in t)
print(json.dumps(dict(failure_tail=[l for l in failure if l.startswith(('dbus.exceptions','AssertionError'))],failed_source_lines=[l for l in failure if 'line ' in l],command_errors=errors,bluez_pid_count=len(subprocess.run(['pidof','bluetoothd'],capture_output=True,text=True).stdout.split()),hci_module_loaded=Path('/sys/module/hci_uart').exists(),hci_controller_present=Path('/sys/class/bluetooth/hci0').exists())))
'''
p=host.ssh('python3 -',input=code.encode());(host.PRIVATE/'reprobe-failure-inspection-private.json').write_bytes(p.stdout);print(p.stdout.decode())
