"""Read-only discovery for the explicitly coordinated device window."""
from pathlib import Path
import json
import os

def read(p):
    try:
        return Path(p).read_text().strip()
    except (OSError, UnicodeError):
        return None

def link(p):
    p = Path(p)
    return str(p.resolve()) if p.exists() else None

data = {'boot_id': read('/proc/sys/kernel/random/boot_id'),
        'release': os.uname().release, 'taint': read('/proc/sys/kernel/tainted')}
data['adapters'] = {p.name: {'name': read(p / 'name'), 'of_node': link(p / 'of_node')}
                    for p in Path('/sys/class/i2c-adapter').glob('i2c-*')}
data['clients'] = {p.name: {'name': read(p / 'name'), 'driver': link(p / 'driver'),
                         'of_node': link(p / 'of_node')}
                   for p in Path('/sys/bus/i2c/devices').glob('*-00*')
                   if p.name.rsplit('-', 1)[-1] in ['0055', '0058', '005c']}
data['supplies'] = {p.name: read(p / 'uevent')
                    for p in Path('/sys/class/power_supply').iterdir()}
data['udc'] = {p.name: {n: read(p / n) for n in
                       ['state', 'current_speed', 'maximum_speed', 'uevent']}
                for p in Path('/sys/class/udc').iterdir()}
data['udc']['dt_usb_psy_names'] = {str(p): p.read_bytes().hex()
    for p in Path('/sys/firmware/devicetree/base').rglob('usb-psy-name')}
data['camera_pm'] = {n: read(Path('/sys/bus/platform/devices') / n / 'power/runtime_status')
    for n in ['ac10000.icp', 'acb3000.camss', 'ac4a000.cci', 'ac4b000.cci']}
data['camera_m2m'] = read('/sys/bus/platform/devices/ac10000.icp/m2m_status')
data['i2c_dev_nodes'] = [str(p) for p in Path('/dev').glob('i2c-*')]
data['tools'] = {p: Path(p).exists() for p in ['/usr/bin/python3', '/usr/bin/cc', '/usr/bin/gcc']}
print(json.dumps(data))
