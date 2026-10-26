from pathlib import Path, PurePosixPath
import hashlib, json, re, tarfile
out = Path('/mnt/e/edk2-samurai-out/kernel97')
files = {}
with tarfile.open(out / 'runtime-retry1.tar') as archive:
    for member in archive:
        if not member.isfile():
            continue
        path = PurePosixPath(member.name)
        assert path.parts[0] == 'k97-runtime-retry1' and '..' not in path.parts
        name = str(PurePosixPath(*path.parts[1:]))
        assert name not in files
        files[name] = archive.extractfile(member).read()
checked = set()
for line in files['SHA256SUMS'].decode().splitlines():
    digest, name = line.split('  ', 1)
    name = name.removeprefix('./')
    assert name not in checked and hashlib.sha256(files[name]).hexdigest() == digest
    checked.add(name)
assert checked == files.keys() - {'SHA256SUMS'}
assert files['result.txt'] == b'RUNTIME_ADDRESS_LIFECYCLE_PASS\n'
query = files['radio-address/current'].decode().strip().split('/')[-1]
for kind in ('wlan', 'bt'):
    raw = files[f'radio-address/{query}/{kind}-dms-response.bin']
    address = files[f'radio-address/{query}/{kind}-mac-le.bin']
    assert len(raw) == 24 and raw[:18] == bytes.fromhex('0201005c0011000204000000000010070006')
    assert raw[18:] == address and len(address) == 6 and any(address) and any(x != 255 for x in address) and not (address[5] & 3)
address = files[f'radio-address/{query}/bt-mac-le.bin']
for name in ('bt-existing.txt', 'bt-start.txt', 'bt-start-repeat.txt'):
    assert 'BT_ADDRESS_VERIFIED index=0 powered=0 connectable=0 bondable=0' in files[name].decode()
for name in ('bt-info-provisioned.txt', 'bt-info-final.txt'):
    payload = bytes.fromhex(re.search(r'command=0x0004 status=0x00 payload=([0-9a-f]+)', files[name].decode()).group(1))
    assert len(payload) == 280 and payload[:6] == address
    assert int.from_bytes(payload[13:17], 'little') & 0x1b == 0
assert 'wpa_state=COMPLETED' in files['wpa-after.txt'].decode() and 'freq=5180' in files['wpa-after.txt'].decode()
assert len(files['nv-check.txt'].decode().splitlines()) == 6
assert all(line.endswith(': OK') for line in files['nv-check.txt'].decode().splitlines())
assert files['persist-check.txt'].decode().strip().endswith(': OK')
vsync = []
for name in ('display-before.txt', 'display-after.txt'):
    line = files[name].decode()
    vsync.append(int(re.search(r'vsync:\s*(\d+)', line).group(1)))
    assert re.search(r'underrun:\s*0\b', line)
assert vsync[1] > vsync[0]
scan = files['bt-scan.txt'].decode()
records = set(re.findall(r'address=([0-9A-F:]+) type=(\d+)', scan))
assert records
dmesg = files['dmesg-after.txt'].decode()
report = dict(runtime_address_lifecycle_pass=True, verified_private_files=len(checked),
              cached_dms_addresses_verified=True, bluetooth_idempotent_start=True,
              scan_only=True, final_bt_powered=False, scan_address_type_records=len(records),
              wifi_5ghz_connected=True, display_vsync=vsync, nv_and_persist_unchanged=True,
              bt_frame_reassembly_errors=dmesg.count('Frame reassembly failed'),
              bt_baudrate_retry_count=dmesg.count('Failed to change controller baudrate'),
              archive_sha256=hashlib.sha256((out / 'runtime-retry1.tar').read_bytes()).hexdigest(),
              goal_complete=False)
(out / 'runtime-validation.json').write_text(json.dumps(report, indent=2) + '\n')
(out / 'address-tools-final.json').write_text(json.dumps({name: hashlib.sha256((out / name).read_bytes()).hexdigest() for name in ('samurai-dms-mac-read', 'samurai-bt-address')}, indent=2) + '\n')
print(json.dumps(report, indent=2))
