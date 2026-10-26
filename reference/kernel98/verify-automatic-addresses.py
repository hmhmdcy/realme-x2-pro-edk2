from pathlib import Path, PurePosixPath
import hashlib, json, re, tarfile

out = Path('/mnt/e/edk2-samurai-out/kernel98')
sha = lambda b: hashlib.sha256(b).hexdigest()
def archive(path, prefix):
    files = {}
    with tarfile.open(path) as handle:
        for member in handle:
            if not member.isfile(): continue
            parts = PurePosixPath(member.name).parts
            assert parts[0] == prefix and '..' not in parts
            name = str(PurePosixPath(*parts[1:]));assert name not in files
            files[name] = handle.extractfile(member).read()
    checked = set()
    for line in files['SHA256SUMS'].decode().splitlines():
        digest,name = line.split('  ',1);name=name.removeprefix('./')
        assert name not in checked and sha(files[name]) == digest
        checked.add(name)
    assert checked == files.keys()-{'SHA256SUMS'}
    return files
files = archive(out/'automatic-addresses.tar', 'k98-automatic-addresses')
before = archive(out/'preflash.tar', 'k98-preflash')
candidate = json.loads((out/'candidate-validation.json').read_text())
state = files['state.txt'].decode().splitlines()
assert state[0] != candidate['before_boot_id'] and state[-2:] == ['0','running']
assert files['result.txt'] == b'AUTO_INDEPENDENT_ADDRESSES_BOOT_PASS\n'
assert files['address-status.txt'] == b'wlan_cache=verified-this-boot\nbt_cache=verified-this-boot\n'
addresses = {}
for kind in ('bt','wlan'):
    root = 'radio-address-before-manual'
    query = files[f'{root}/current-{kind}'].decode().strip().split('/')[-1]
    assert files[f'{root}/{query}/boot-id'].decode().strip() == state[0]
    address = files[f'{root}/{query}/{kind}-mac-le.bin']
    raw = files[f'{root}/{query}/{kind}-dms-response.bin']
    assert len(address)==6 and any(address) and any(x!=255 for x in address) and not(address[5]&3)
    assert len(raw)==24 and raw[:18]==bytes.fromhex('0201005c0011000204000000000010070006') and raw[18:]==address
    opposite='wlan' if kind=='bt' else 'bt'
    assert f'{root}/{query}/{opposite}-mac-le.bin' not in files
    prior = before[f'samurai-radio-address/current-{kind}'].decode().strip().split('/')[-1]
    assert address == before[f'samurai-radio-address/{prior}/{kind}-mac-le.bin']
    addresses[kind] = address
payload = bytes.fromhex(re.search(r'command=0x0004 status=0x00 payload=([0-9a-f]+)',files['bt-before-manual.txt'].decode())[1])
assert len(payload)==280 and payload[:6]==addresses['bt'] and int.from_bytes(payload[13:17],'little')&0x1b==0
assert bytes.fromhex(files['wlan-before-manual.txt'].decode().strip().replace(':','')) == addresses['wlan'][::-1]
wifi=files['samurai-wifi-boot.log'].decode();bt=files['samurai-bluetooth-boot.log'].decode()
timings={kind:float(re.search(r'RADIO_ADDRESS_QUERY_VERIFIED kind='+kind+r' uptime=([\d.]+)',data)[1]) for kind,data in [('wlan',wifi),('bt',bt)]}
assert 'BT_ADDRESS_VERIFIED index=0 powered=0 connectable=0 bondable=0' in bt
assert b'ath10k:ath10k_log_dbg\n' in files['available-events.txt']
display=files['display.txt'].decode()
assert re.search(r'underrun:\s*0\b',display) and int(re.search(r'frame_done_cnt:(\d+)',display)[1]) == 0
dmesg=files['dmesg.txt'].decode()
errors=[dict(phase=int(a),requested_baud=int(b),chunk=int(c),partial=int(d),first=e) for a,b,c,d,e in re.findall(r'Frame reassembly failed \(-84\) phase=(\d+) baud=(\d+) chunk=(\d+) partial=(\d+) first=([0-9a-f]{2})',dmesg)]
assert len(errors)==dmesg.count('Frame reassembly failed')==2
assert all(x==dict(phase=2,requested_baud=115200,chunk=1,partial=0,first='00') for x in errors)
report=dict(automatic_address_audit_pass=True,kernel_build=97,logical_stage=98,
    verified_private_files=len(files)-1,independent_address_queries_automatic=True,
    query_uptimes=timings,dms_addresses_cross_boot_equal=True,addresses_verified_before_manual_calls=True,
    ath10k_filtered_trace_available=True,bt_boot_error_observations=errors,
    bt_boot_error_phase='power_on_pulse',baudrate_error_hypothesis_confirmed=False,
    final_boot_snapshot_bt_powered=False,display_boot_frame_timeouts=0,goal_complete=False,
    archive_sha256=sha((out/'automatic-addresses.tar').read_bytes()))
(out/'automatic-addresses-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
