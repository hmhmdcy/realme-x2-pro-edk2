"""Decode only root's already captured76-byte GET_NODE_INFORMATION record."""
from pathlib import Path
import base64
import hashlib
import json
import struct

root = Path(__file__).resolve().parent
path = Path('E:/edk2-samurai-out/charging-management-20261023/usb500-baseline-r6-host-01/metadata-private.json')
data = path.read_bytes()
metadata = json.loads(data)
raw = base64.b64decode(metadata['NodeBase64'], validate=True)
# USB_NODE_INFORMATION enum prefix and packed HubDescriptor layout already
# pinned by the parent to its SDK10.0.26100.0 headers. Do not infer another ABI.
assert metadata['WindowsSdk'] == '10.0.26100.0'
assert len(raw) == 76 and struct.unpack_from('<I', raw)[0] == 0
descriptor = raw[4:]
length, kind, ports, characteristics, good, current = struct.unpack_from('<BBB HBB', descriptor)
assert kind == 0x29 and ports == 7 and length == 9
width = (ports + 1 + 7) // 8
assert length == 7 + 2 * width
removable = int.from_bytes(descriptor[7:7 + width], 'little')
mask = int.from_bytes(descriptor[7 + width:7 + 2 * width], 'little')
assert raw[75] in (0, 1) and bool(raw[75]) == metadata['HubIsBusPowered']
result = {
    'cached_source': str(path), 'source_sha256': hashlib.sha256(data).hexdigest(),
    'captured_sdk': metadata['WindowsSdk'], 'node_bytes': len(raw),
    'hub_descriptor_length': length, 'ports': ports,
    'wHubCharacteristics': characteristics, 'power_good_2ms_units': good,
    'hub_controller_current_ma': current, 'DeviceRemovable_bitmap': removable,
    'PortPwrCtrlMask_bitmap': mask, 'HubIsBusPowered': bool(raw[75]),
    'ports_declared_non_removable': [i for i in range(1, ports + 1) if removable & (1 << i)],
    'port7_declared_removable': not bool(removable & (1 << 7)),
    'descriptor_hardware_origin_proved': False,
    'failure_time_power_rejection_proved': False,
    'phone_or_usb_api_accessed': False,
}
(root / 'cached-node-result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
