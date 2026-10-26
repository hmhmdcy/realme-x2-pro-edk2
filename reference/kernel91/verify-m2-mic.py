"""Verify captured host M2 MICs without printing identities or key material.

Input files stay in the private output directory. Passing this check proves
the supplied PMK was used consistently; it does not prove the AP shares it.
"""
from pathlib import Path
import hashlib, hmac, json, re

out = Path('/mnt/e/edk2-samurai-out/kernel91')
conf = (out / 'wpa-test-private.conf').read_text()
pmk = bytes.fromhex(re.search(r'^\s*psk=([0-9a-f]{64})$', conf, re.M).group(1))
text = (out / 'handshake-wpa.txt').read_text()
addrs = nonces = None
checked = failed = 0
for line in text.splitlines():
    m = re.search(r'WPA: PTK derivation - A1=([0-9a-f:]+) A2=([0-9a-f:]+)', line)
    if m:
        addrs = sorted(bytes.fromhex(x.replace(':', '')) for x in m.groups())
        nonces = {}
    m = re.search(r'WPA: Nonce([12]) - hexdump\(len=32\): ([0-9a-f ]+)$', line)
    if m and nonces is not None:
        nonces[m.group(1)] = bytes.fromhex(m.group(2))
    m = re.search(r'WPA: TX EAPOL-Key - hexdump\(len=(\d+)\): ([0-9a-f ]+)$', line)
    if not m:
        continue
    packet = bytearray.fromhex(m.group(2))
    assert len(packet) == int(m.group(1)) and len(packet) >= 99
    info = int.from_bytes(packet[5:7], 'big')
    # Descriptor v2, pairwise M2: MIC set, ACK/INSTALL/SECURE clear.
    if info & 7 != 2 or not info & 0x100 or info & (0x80 | 0x40 | 0x200):
        continue
    assert addrs and nonces and len(nonces) == 2
    context = b''.join(addrs) + b''.join(sorted(nonces.values()))
    kck = hmac.digest(pmk, b'Pairwise key expansion\0' + context + b'\0', 'sha1')[:16]
    recorded = bytes(packet[81:97])
    packet[81:97] = bytes(16)
    valid = hmac.compare_digest(recorded, hmac.digest(kck, packet, 'sha1')[:16])
    checked += 1
    failed += not valid
result = {'m2_mic_checked': checked, 'm2_mic_failed': failed, 'independent_reference': 'Python hashlib/hmac', 'proves_ap_password_match': False}
(out / 'm2-mic-check.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
assert checked > 0 and failed == 0
