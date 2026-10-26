from pathlib import Path, PurePosixPath
import hashlib, json, re, tarfile

out = Path('/mnt/e/edk2-samurai-out/kernel98')
files = {}
with tarfile.open(out / 'independent-addresses.tar') as archive:
    for member in archive:
        if not member.isfile():
            continue
        path = PurePosixPath(member.name)
        assert path.parts[0] == 'k98-independent-addresses' and '..' not in path.parts
        name = str(PurePosixPath(*path.parts[1:]))
        assert name not in files and member.uid == 0
        files[name] = archive.extractfile(member).read()
checked = set()
for line in files['SHA256SUMS'].decode().splitlines():
    digest, name = line.split('  ', 1)
    name = name.removeprefix('./')
    assert name not in checked and hashlib.sha256(files[name]).hexdigest() == digest
    checked.add(name)
assert checked == files.keys() - {'SHA256SUMS'}
assert files['result.txt'] == b'INDEPENDENT_QUERY_FAILURE_ISOLATION_PASS\n'
assert files['exit-status.txt'] == b'0\n' and files['wlan-injected-exit.txt'] == b'42\n'
assert files['after-wlan-failure.txt'] == b'wlan_cache=unavailable\nbt_cache=unavailable\n'
assert files['after-bt-query.txt'] == b'wlan_cache=unavailable\nbt_cache=verified-this-boot\n'
assert files['final-address-status.txt'] == b'wlan_cache=verified-this-boot\nbt_cache=verified-this-boot\n'
assert files['wlan-before.txt'] == files['wlan-after.txt']
for name in ('helper-restore.txt', 'helper-restored-before-wlan.txt'):
    assert files[name].decode().strip().endswith(': OK')
old = files['cache-before/current'].decode().strip().split('/')[-1]
addresses = {}
for kind in ('wlan', 'bt'):
    query = files[f'cache-after/current-{kind}'].decode().strip().split('/')[-1]
    address = files[f'cache-after/{query}/{kind}-mac-le.bin']
    response = files[f'cache-after/{query}/{kind}-dms-response.bin']
    assert len(address) == 6 and any(address) and any(x != 255 for x in address) and not (address[5] & 3)
    assert len(response) == 24 and response[:18] == bytes.fromhex('0201005c0011000204000000000010070006')
    assert response[18:] == address == files[f'cache-before/{old}/{kind}-mac-le.bin']
    opposite = 'bt' if kind == 'wlan' else 'wlan'
    assert f'cache-after/{query}/{opposite}-mac-le.bin' not in files
    addresses[kind] = address
payload = bytes.fromhex(re.search(r'command=0x0004 status=0x00 payload=([0-9a-f]+)', files['bt-final.txt'].decode())[1])
assert len(payload) == 280 and payload[:6] == addresses['bt'] and int.from_bytes(payload[13:17], 'little') & 0x1b == 0
assert bytes.fromhex(files['wlan-after.txt'].decode().strip().replace(':', '')) == addresses['wlan'][::-1]
assert 'wpa_state=COMPLETED\n' in files['wpa-final.txt'].decode() and 'freq=5180\n' in files['wpa-final.txt'].decode()
assert files['state.txt'].decode().splitlines()[-2:] == ['0', 'running']
values = []
for name in ('display-before.txt', 'display-after.txt'):
    text = files[name].decode()
    assert re.search(r'underrun:\s*0\b', text)
    values.append(int(re.search(r'vsync:\s*(\d+)', text)[1]))
assert values[1] > values[0]
report = dict(address_isolation_audit_pass=True, verified_private_files=len(checked),
    injected_wlan_query_failure_exit=42, real_bt_dms_query_despite_wlan_failure=True,
    per_radio_private_caches_verified=True, helper_restored_byte_identical=True,
    wifi_address_and_connection_unchanged=True, final_bt_powered=False,
    fresh_offline_identity_tested=False, genuine_cold_wifi_failure_tested=False,
    archive_sha256=hashlib.sha256((out / 'independent-addresses.tar').read_bytes()).hexdigest(), goal_complete=False)
(out / 'address-isolation-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
