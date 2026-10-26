from pathlib import Path, PurePosixPath
import hashlib, json, re, tarfile

out = Path('/mnt/e/edk2-samurai-out/kernel98')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel98')
sha = lambda data: hashlib.sha256(data).hexdigest()

def archive(path, root):
    files = {}
    with tarfile.open(path) as handle:
        for member in handle:
            if not member.isfile():
                continue
            parts = PurePosixPath(member.name).parts
            assert parts[0] == root and '..' not in parts
            name = str(PurePosixPath(*parts[1:]))
            assert name not in files
            files[name] = handle.extractfile(member).read()
    checked = set()
    for line in files['SHA256SUMS'].decode().splitlines():
        digest, name = line.split('  ', 1)
        name = name.removeprefix('./')
        assert name not in checked and sha(files[name]) == digest
        checked.add(name)
    assert checked == files.keys() - {'SHA256SUMS'}
    return files

files = archive(out / 'checkpoint-final.tar', 'k98-checkpoint-final')
before = archive(out / 'preflash.tar', 'k98-preflash')
candidate = json.loads((out / 'candidate-validation.json').read_text())
state = files['state.txt'].decode().splitlines()
assert '#97 SMP PREEMPT' in state[0] and state[1] != candidate['before_boot_id']
assert state[3:5] == ['0', 'running'] and 'fb0' in state and 'card1-DSI-1' in state
assert files['boot-finished'] == b'0\n'
assert files['address-status.txt'] == b'wlan_cache=verified-this-boot\nbt_cache=verified-this-boot\n'
assert b'wpa_state=COMPLETED\n' in files['wpa-status.txt'] and b'freq=5180\n' in files['wpa-status.txt']

for filename, root, nested, reportname in (
    ('automatic-addresses.tar', 'k98-automatic-addresses', 'tests/k98-automatic-addresses/', 'automatic-addresses-validation.json'),
    ('trace-connectivity.tar', 'k98-trace-connectivity', 'tests/k98-trace-connectivity/', 'trace-validation.json'),
):
    original = archive(out / filename, root)
    assert all(files[nested + name] == data for name, data in original.items())
    report = json.loads((out / reportname).read_text())
    assert report['archive_sha256'] == sha((out / filename).read_bytes())

addresses = {}
for kind in ('wlan', 'bt'):
    root = 'samurai-radio-address'
    query = files[f'{root}/current-{kind}'].decode().strip().split('/')[-1]
    assert re.fullmatch(r'query\.[A-Za-z0-9]{6}', query)
    assert files[f'{root}/{query}/boot-id'].decode().strip() == state[1]
    address = files[f'{root}/{query}/{kind}-mac-le.bin']
    raw = files[f'{root}/{query}/{kind}-dms-response.bin']
    assert len(address) == 6 and any(address) and any(x != 255 for x in address) and not (address[5] & 3)
    assert len(raw) == 24 and raw[:18] == bytes.fromhex('0201005c0011000204000000000010070006') and raw[18:] == address
    opposite = 'bt' if kind == 'wlan' else 'wlan'
    assert f'{root}/{query}/{opposite}-mac-le.bin' not in files
    prior = before[f'{root}/current-{kind}'].decode().strip().split('/')[-1]
    assert address == before[f'{root}/{prior}/{kind}-mac-le.bin']
    addresses[kind] = address
assert bytes.fromhex(files['wlan-address.txt'].decode().strip().replace(':', '')) == addresses['wlan'][::-1]
payload = bytes.fromhex(re.search(r'command=0x0004 status=0x00 payload=([0-9a-f]+)', files['bt-info.txt'].decode())[1])
assert len(payload) == 280 and payload[:6] == addresses['bt'] and int.from_bytes(payload[13:17], 'little') & 0x1b == 0
assert 'command=0x0003 status=0x00 payload=01000000' in files['bt-info.txt'].decode()
assert files['services/nv-source-hashes.txt'] == before['nv-source-hashes.txt']
assert len(files['nv-source-check.txt'].decode().splitlines()) == 6
assert all(line.endswith(': OK') for line in files['nv-source-check.txt'].decode().splitlines())
assert files['persist-check.txt'] == b'/dev/sda2: OK\n'

def cpio_content(path):
    data = path.read_bytes(); offset = 0; result = {}
    align = lambda n: (n + 3) & ~3
    while offset + 110 <= len(data):
        assert data[offset:offset+6] == b'070701'
        fields = [int(data[offset+6+i*8:offset+14+i*8], 16) for i in range(13)]
        start = offset + 110
        name = data[start:start+fields[11]-1].decode()
        start = align(start + fields[11]); content = data[start:start+fields[6]]
        offset = align(start + fields[6])
        if name == 'TRAILER!!!':
            return result
        assert name not in result
        result[name] = content
    raise AssertionError('Missing CPIO trailer')

installed = cpio_content(out / 'cpio-after')
readback = {name: digest for digest, name in (line.split('  ', 1) for line in files['deployment-readback.txt'].decode().splitlines())}
assert readback['-'] == candidate['boot_sha256']
assert readback['/dev/sde11'] == candidate['full_backup_boot_sha256']
assert readback['/dev/sde32'] == candidate['logdump_sha256']
assert readback['/init'] == sha((out / 'init-before').read_bytes()) == sha(installed['init'])
for name in ('samurai-wifi', 'samurai-bluetooth', 'samurai-radio-address', 'samurai-dms-mac-read', 'samurai-bt-address'):
    assert readback['/usr/sbin/' + name] == sha(installed['usr/sbin/' + name])
assert installed['usr/sbin/samurai-radio-address'] == (ref / 'samurai-radio-address').read_bytes()
for name in ('btbcm', 'btqca', 'hci_uart'):
    assert readback[f'/lib/modules/samurai/{name}.ko'] == sha(installed[f'lib/modules/samurai/{name}.ko']) == sha((out / (name + '.ko')).read_bytes())

traffic, internet = {}, {}
for phase, network, frequency in (('initial-retry1', 'initial', 2462), ('five-ghz', 'five-ghz', 5180)):
    network_log = (out / ('two-ghz-network.log' if network == 'initial' else 'five-ghz-network.log')).read_text()
    for marker in ('GATEWAY_PING=PASS', 'DNS_LOOKUP=PASS', 'HTTP_FETCH=PASS', 'NETWORK_OBSERVATION_PASS'):
        assert marker in network_log
    status = files[f'tests/k98-{network}-network/status.txt'].decode()
    assert 'wpa_state=COMPLETED\n' in status and f'freq={frequency}\n' in status
    http = files[f'tests/k98-{network}-network/http.txt']
    assert len(http) == 577 and sha(http) in network_log
    internet[phase] = re.search(r'INTERNET_PING=(PASS|FAIL)', network_log)[1]
    server_log = files[f'tests/k98-{phase}-traffic-server.log'].decode()
    assert 'WIFI_TX_BYTES=4194304' in server_log and 'WIFI_RX_BYTES=4194304' in server_log
    sums = files[f'tests/k98-{phase}-traffic-sha.txt'].decode().splitlines()
    assert len(sums) == 2
    values = []
    for line, filename in zip(sums, ('traffic-download.bin', 'traffic-upload-source.bin')):
        data = (out / f'traffic-{phase}' / filename).read_bytes()
        assert len(data) == 4194304 and sha(data) == line.split()[0]
        values.append(sha(data))
    traffic[phase] = values
assert files['tests/k98-initial-traffic-server.log'] == b'WIFI_TRAFFIC_READY\n'

dmesg = files['dmesg.txt'].decode()
for forbidden in ('failed to assign msa map permissions', 'failed to unmap msa permissions', 'TLV tx timeout', 'Fatal error received'):
    assert forbidden not in dmesg, forbidden
errors = re.findall(r'Frame reassembly failed \(-84\) phase=(\d+) baud=(\d+) chunk=(\d+) partial=(\d+) first=([0-9a-f]{2})', dmesg)
assert len(errors) == dmesg.count('Frame reassembly failed') == 3
assert all(x == ('2', '115200', '1', '0', '00') for x in errors)
display_timeouts = [float(x) for x in re.findall(r'^\[\s*([\d.]+)\].*frame done timeout', dmesg, re.M)]
assert len(display_timeouts) == 1
trace_before = files['tests/k98-trace-connectivity/dmesg-before.txt'].decode()
assert trace_before.count('frame done timeout') == 1
reasons = re.findall(r'CTRL-EVENT-DISCONNECTED[^\n]*reason=(\d+)', files['services/wpa.log'].decode())
assert reasons == ['7', '3', '7']
disconnect_uptimes = [float(x) for x in re.findall(r'^\[\s*([\d.]+)\].*Reason: 7=', dmesg, re.M)]
assert len(disconnect_uptimes) == 2
assert dmesg.count('failed to install key') == 6
assert all('-110' in line for line in dmesg.splitlines() if 'failed to install key' in line)
display = state[-1]
assert re.search(r'underrun:\s*0\b', display) and int(re.search(r'frame_done_cnt:(\d+)', display)[1]) == 1
trace_report = json.loads((out / 'trace-validation.json').read_text())
assert trace_report['pairwise_delete_security_indications'] == 0
assert trace_report['key_wait_behavior_unchanged'] and not trace_report['uninterrupted_scan_coexistence_pass']
report = dict(evidence_audit_pass=True, kernel_build=97, logical_stage=98,
    verified_private_files=len(files)-1, checkpoint_sha256=sha((out / 'checkpoint-final.tar').read_bytes()),
    deployment_readback_verified=True, nv_and_persist_unchanged=True,
    dms_addresses_cross_boot_equal=True, runtime_wlan_and_bt_addresses_verified=True,
    automatic_address_provisioning=True, automatic_ap_connection=False, dual_radio_cache_dependency_remaining=False,
    independent_queries_fault_isolation_tested=True, real_wifi_boot_failure_tested=False,
    final_bt_powered=False, incoming_connectable=False, discoverable=False, bondable=False,
    bt_pairing_connection_tested=False, cold_power_boot_tested=False, fresh_offline_bt_identity_tested=False,
    unforced_wifi_disconnects=2, unforced_disconnect_uptimes=disconnect_uptimes,
    second_disconnect_bt_off=True, first_disconnect_root_cause_resolved=False,
    key_delete_waits_ms=trace_report['pairwise_delete_waits_ms'], key_wait_behavior_unchanged=True,
    key_operation_timeout_warnings=6, snapshots_missed_transient_disconnect=True, uninterrupted_scan_coexistence_pass=False,
    display_frame_done_timeout_count=1, display_frame_done_timeout_uptimes=display_timeouts,
    display_timeout_preceded_wifi_connection_and_scan=True, display_wifi_failure_causality_proven=False,
    traffic_sha256=traffic, internet_ping_results=internet,
    bt_baudrate_retry_count=dmesg.count('Failed to change controller baudrate'),
    bt_frame_reassembly_error_count=3, bt_error_phase='power_on_pulse', single_zero_byte_observed=True,
    nfc_new_test_this_stage=False, previous_nfc_controller_proof_preserved=True,
    failed_attempts_preserved=True, goal_complete=False)
(out / 'checkpoint-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
