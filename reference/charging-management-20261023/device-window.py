"""Use the established strict SSH transport only inside a coordinated window."""
from pathlib import Path
import importlib.util
import json
import shlex
import sys

ref = Path(__file__).resolve().parent
private = Path('/mnt/e/edk2-samurai-out/charging-management-20261023/window2')
private.mkdir(parents=True, exist_ok=True, mode=0o700)
spec = importlib.util.spec_from_file_location('camera_transport', ref.parent / 'kernel441/host.py')
host = importlib.util.module_from_spec(spec)
spec.loader.exec_module(host)
ipv6_endpoint = ref.parent.parent.parent / 'edk2-samurai-out/charging-management-20261023/r7-postboot/usb-ipv6-transport-private.json'
if ipv6_endpoint.exists():
    transport_spec = importlib.util.spec_from_file_location('charging_usb_ipv6', ref / 'r7-transport.py')
    transport = importlib.util.module_from_spec(transport_spec)
    transport_spec.loader.exec_module(transport)
    host.raw_ssh = transport.raw_ssh
eud_endpoint = ref.parent.parent.parent / 'edk2-samurai-out/charging-management-20261023/eud-boot-activation/eud-boot-r2-live-001/new-endpoint-private.json'
if eud_endpoint.exists():
    transport_spec = importlib.util.spec_from_file_location('charging_eud_postboot', ref / 'eud-postboot-transport.py')
    transport = importlib.util.module_from_spec(transport_spec)
    transport_spec.loader.exec_module(transport)
    host.raw_ssh = transport.raw_ssh
camera_ssh = host.ssh

def charging_ssh(command, **kwargs):
    adoption = ref.parent.parent.parent / 'edk2-samurai-out/charging-management-20261023/boot-adoption-private.json'
    if not adoption.exists(): return camera_ssh(command, **kwargs)
    data = json.loads(adoption.read_text())
    assert data['original_key_verified'] and (data.get('baseline440_verified') or data.get('baseline481_verified'))
    host.raw_ssh('cmp -s /proc/sys/kernel/random/boot_id ' + shlex.quote(data['guard_path']), timeout=15).check_returncode()
    return host.raw_ssh(command, **kwargs)

host.ssh = charging_ssh

if __name__ == '__main__':
    assert len(sys.argv) == 2 and sys.argv[1] in ['before', 'after']
    name = sys.argv[1]
    q = host.ssh('python3 -c ' + shlex.quote((ref / 'observe-device.py').read_text()), timeout=35)
    q.check_returncode()
    data = json.loads(q.stdout)
    (private / (name + '-private.json')).write_bytes(q.stdout)
    # Exclude boot identifiers and raw supplier data from public output.
    print(json.dumps({k: data[k] for k in ['release', 'taint', 'clients', 'adapters',
                       'udc', 'camera_pm', 'i2c_dev_nodes', 'tools']}, indent=2))
