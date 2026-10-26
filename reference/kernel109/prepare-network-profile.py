"""Convert the existing private Wi-Fi profile to a private NM keyfile."""
from pathlib import Path
import re, shlex, uuid, os
os.umask(0o077)
out = Path('/mnt/e/edk2-samurai-out/kernel109')
source = (out/'wpa-2g-private.conf').read_text()
values = {}
for field in ('ssid', 'psk'):
    found = re.findall(r'^\s*'+field+r'\s*=\s*(.+?)\s*$', source, re.M)
    assert len(found) == 1, f'Expected exactly one {field}'
    if field == 'ssid' and not found[0].startswith('"'):
        # wpa_supplicant accepts an unquoted SSID as hexadecimal bytes.
        # A NM keyfile accepts a human-readable UTF-8 string here.
        values[field] = bytes.fromhex(found[0]).decode('utf-8')
    else:
        values[field] = shlex.split(found[0])[0]
    assert '\n' not in values[field] and '\r' not in values[field]
def escape(value):
    return value.replace('\\', '\\\\').replace(';', '\\;')
text = f'''[connection]
id=Samurai 2.4GHz
uuid={uuid.uuid4()}
type=wifi
interface-name=wlan0
autoconnect=true

[wifi]
mode=infrastructure
ssid={escape(values['ssid'])}
band=bg
cloned-mac-address=preserve

[wifi-security]
key-mgmt=wpa-psk
psk={escape(values['psk'])}

[ipv4]
method=auto

[ipv6]
method=disabled
'''
path = out/'samurai-wifi-private.nmconnection'
path.write_text(text)
path.chmod(0o600)
print('PRIVATE_NM_PROFILE_READY')
