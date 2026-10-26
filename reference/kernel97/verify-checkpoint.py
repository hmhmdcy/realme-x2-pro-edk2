from pathlib import Path, PurePosixPath
import hashlib, json, re, tarfile

out = Path('/mnt/e/edk2-samurai-out/kernel97')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel97')
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

files = archive(out / 'checkpoint-final.tar', 'k97-checkpoint-final')
before = archive(out / 'preflash.tar', 'k97-preflash-retry1')
candidate = json.loads((out / 'candidate-validation.json').read_text())
state = files['state.txt'].decode().splitlines()
assert '#96 SMP PREEMPT' in state[0] and state[1] != candidate['before_boot_id']
assert state[3:5] == ['0', 'running'] and 'fb0' in state and 'card1-DSI-1' in state
assert files['boot-finished'] == b'0\n'
assert files['tests/k97-initial/auto-address-result.txt'] == b'AUTO_ADDRESS_BOOT_PASS\n'
assert b'wpa_state=COMPLETED\n' in files['wpa-status.txt'] and b'freq=5180\n' in files['wpa-status.txt']

def identities(collection, base, expected_boot=None):
    query = collection[base + '/current'].decode().strip().split('/')[-1]
    assert re.fullmatch(r'query\.[A-Za-z0-9]{6}', query)
    if expected_boot:
        assert collection[f'{base}/{query}/boot-id'].decode().strip() == expected_boot
    result = {}
    for kind in ('wlan', 'bt'):
        address = collection[f'{base}/{query}/{kind}-mac-le.bin']
        response = collection[f'{base}/{query}/{kind}-dms-response.bin']
        assert len(address) == 6 and any(address) and any(x != 255 for x in address) and not (address[5] & 3)
        assert len(response) == 24 and response[:18] == bytes.fromhex('0201005c0011000204000000000010070006')
        assert response[18:] == address
        result[kind] = address
    return result

addresses = identities(files, 'radio-address', state[1])
assert addresses == identities(files, 'tests/k97-initial/radio-address-before-manual', state[1])
assert addresses == identities(before, 'samurai-radio-address', candidate['before_boot_id'])
for name in ('wlan-address.txt', 'tests/k97-initial/wlan-address-before-manual.txt'):
    assert bytes.fromhex(files[name].decode().strip().replace(':', '')) == addresses['wlan'][::-1]

def bt_info(name, powered):
    data = files[name].decode()
    payload = bytes.fromhex(re.search(r'command=0x0004 status=0x00 payload=([0-9a-f]+)', data)[1])
    assert len(payload) == 280 and payload[:6] == addresses['bt']
    settings = int.from_bytes(payload[13:17], 'little')
    assert settings & 0x1b == int(powered)
    assert 'command=0x0003 status=0x00 payload=01000000' in data

bt_info('tests/k97-initial/bt-info-before-manual.txt', False)
bt_info('tests/k97-initial/bt-powered-info.txt', True)
bt_info('tests/k97-retry1-bt-powered-info.txt', True)
bt_info('bt-info-final.txt', False)
assert 'command=0x0005 status=0x00' in files['bt-off.txt'].decode()
wifi_log = files['samurai-wifi-boot.log'].decode()
bt_log = files['samurai-bluetooth-boot.log'].decode()
for marker in ('RADIO_ADDRESS_QUERY_VERIFIED', 'WLAN_ADDRESS_VERIFIED', 'WIFI_READY'):
    assert marker in wifi_log
assert 'WIFI_BOOTSTRAP_FINISHED result=0' in bt_log
assert 'BT_ADDRESS_VERIFIED index=0 powered=0 connectable=0 bondable=0' in bt_log
assert 'BT_ADDRESS_READY' in bt_log
boot_timings = {marker: float(re.search(marker + r' uptime=([\d.]+)', data)[1]) for marker, data in (
    ('RADIO_ADDRESS_QUERY_VERIFIED', wifi_log), ('WLAN_ADDRESS_VERIFIED', wifi_log),
    ('BT_DRIVER_REGISTERED', bt_log), ('BT_ADDRESS_READY', bt_log))}
assert files['services/nv-source-hashes.txt'] == before['nv-source-hashes.txt']
assert len(files['nv-source-check.txt'].decode().splitlines()) == 6
assert all(line.endswith(': OK') for line in files['nv-source-check.txt'].decode().splitlines())
assert files['persist-check.txt'] == b'/dev/sda2: OK\n'
readback = {name: digest for digest, name in (line.split('  ', 1) for line in files['deployment-readback.txt'].decode().splitlines())}
assert readback['-'] == candidate['boot_sha256']
assert readback['/dev/sde11'] == candidate['full_backup_boot_sha256']
assert readback['/dev/sde32'] == candidate['logdump_sha256']
assert readback['/init'] == sha((out / 'init-before').read_bytes())
for name in ('samurai-wifi', 'samurai-bluetooth', 'samurai-radio-address'):
    assert readback['/usr/sbin/' + name] == sha((ref / name).read_bytes())
for name in ('samurai-dms-mac-read', 'samurai-bt-address'):
    assert readback['/usr/sbin/' + name] == sha((out / name).read_bytes())
for name in ('btbcm', 'btqca', 'hci_uart'):
    assert readback[f'/lib/modules/samurai/{name}.ko'] == sha((out.parent / 'kernel94' / (name + '.ko')).read_bytes())

displays, scan_counts, observations = {}, {}, {}
for phase in ('wifi-only', 'initial-retry1', 'five-ghz'):
    suffix = '' if phase == 'wifi-only' else '-coexistence'
    log = files[f'tests/k97-{phase}{suffix}.log'].decode()
    marker = 'WIFI_ONLY_OBSERVATION_PASS' if phase == 'wifi-only' else 'COEXISTENCE_OBSERVATION_PASS'
    assert marker in log
    pattern = (r'^sample=(\d+) uptime=([\d.]+) BT=off WPA=COMPLETED MPSS=running taint=0$' if phase == 'wifi-only'
               else r'^sample=(\d+) uptime=([\d.]+) MPSS=running WPA=COMPLETED DRM=present taint=0$')
    samples = re.findall(pattern, log, re.M)
    assert [int(x[0]) for x in samples] == list(range(1, 46))
    assert float(samples[-1][1]) - float(samples[0][1]) >= 88
    observations[phase] = [float(samples[0][1]), float(samples[-1][1])]
    values = []
    for position in ('before', 'after'):
        display = files[f'tests/k97-{phase}{suffix}/display-{position}.txt'].decode()
        assert re.search(r'underrun:\s*0\b', display)
        values.append(int(re.search(r'vsync:\s*(\d+)', display)[1]))
    assert values[1] > values[0]
    displays[phase] = values
    if suffix:
        scan = files[f'tests/k97-{phase}{suffix}/bt-scan.txt'].decode()
        assert 'command=0x0023 status=0x00' in scan and 'discovering=0' in scan
        records = set(re.findall(r'address=([0-9A-F:]+) type=(\d+)', scan))
        assert records
        scan_counts[phase] = len(records)
traffic, internet = {}, {}
for phase, network, frequency in (('initial-retry1', 'initial-retry1', 2462), ('five-ghz', 'five-ghz-retry1', 5180)):
    network_log = files[f'tests/k97-{network}-network.log'].decode()
    for marker in ('GATEWAY_PING=PASS', 'DNS_LOOKUP=PASS', 'HTTP_FETCH=PASS', 'NETWORK_OBSERVATION_PASS'):
        assert marker in network_log
    status = files[f'tests/k97-{network}-network/status.txt'].decode()
    assert 'wpa_state=COMPLETED\n' in status and f'freq={frequency}\n' in status
    http = files[f'tests/k97-{network}-network/http.txt']
    assert len(http) == 577 and sha(http) in network_log
    internet[phase] = re.search(r'INTERNET_PING=(PASS|FAIL)', network_log)[1]
    server_log = files[f'tests/k97-{phase}-traffic-server.log'].decode()
    assert 'WIFI_TX_BYTES=4194304' in server_log and 'WIFI_RX_BYTES=4194304' in server_log
    sums = files[f'tests/k97-{phase}-traffic-sha.txt'].decode().splitlines()
    assert len(sums) == 2
    values = []
    for line, filename in zip(sums, ('traffic-download.bin', 'traffic-upload-source.bin')):
        data = (out / f'traffic-{phase}' / filename).read_bytes()
        assert len(data) == 4194304 and sha(data) == line.split()[0]
        values.append(sha(data))
    traffic[phase] = values

# Preserve and explicitly classify failures instead of using later passes to erase them.
first_log = files['tests/k97-initial-coexistence.log'].decode()
assert first_log.count('sample=') == 2 and 'COEXISTENCE_OBSERVATION_PASS' not in first_log
first_wpa = files['tests/k97-first-disconnect/wpa.log'].decode()
reasons = re.findall(r'CTRL-EVENT-DISCONNECTED[^\n]*reason=(\d+)', first_wpa)
assert reasons == ['7']
assert 'failed to install key' in files['tests/k97-first-disconnect/dmesg.txt'].decode()
assert not files['tests/k97-initial-network.log'] and not files['tests/k97-five-ghz-network.log']
dmesg = files['dmesg.txt'].decode()
for forbidden in ('failed to assign msa map permissions', 'failed to unmap msa permissions', 'TLV tx timeout', 'Fatal error received'):
    assert forbidden not in dmesg, forbidden
display_timeouts = [float(value) for value in re.findall(r'^\[\s*([\d.]+)\].*frame done timeout', dmesg, re.M)]
assert len(display_timeouts) == 3
for phase in ('wifi-only', 'initial-retry1-coexistence', 'five-ghz-coexistence'):
    assert files[f'tests/k97-{phase}/dmesg-after.txt'].decode().count('frame done timeout') == len(display_timeouts)
report = dict(evidence_audit_pass=True, kernel_build=96, logical_stage=97,
    verified_private_files=len(files)-1, checkpoint_sha256=sha((out / 'checkpoint-final.tar').read_bytes()),
    deployment_readback_verified=True, nv_and_persist_unchanged=True,
    dms_addresses_cross_boot_equal=True, runtime_wlan_and_bt_addresses_verified=True,
    automatic_address_provisioning=True, automatic_ap_connection=False, boot_address_timings=boot_timings,
    final_bt_powered=False, incoming_connectable=False, discoverable=False, bondable=False,
    bt_pairing_connection_tested=False, cold_power_boot_tested=False, fresh_offline_bt_identity_tested=False,
    dual_radio_cache_dependency_remaining=True, unforced_wifi_disconnects=1, first_disconnect_reason=7,
    first_disconnect_root_cause_resolved=False, failed_attempts_preserved=True,
    initial_coexistence_pass=False, display_frame_done_timeout_count=len(display_timeouts),
    display_frame_done_timeout_uptimes=display_timeouts, display_wifi_failure_causality_proven=False,
    new_display_timeouts_during_later_observations=False,
    coexistence_samples_per_phase=45, scan_address_type_counts=scan_counts,
    display_vsync_windows=displays, observation_uptime_windows=observations,
    traffic_sha256=traffic, internet_ping_results=internet,
    bt_baudrate_retry_count=dmesg.count('Failed to change controller baudrate'),
    bt_frame_reassembly_error_count=dmesg.count('Frame reassembly failed'),
    nfc_new_test_this_stage=False, previous_nfc_controller_proof_preserved=True, goal_complete=False)
(out / 'checkpoint-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
