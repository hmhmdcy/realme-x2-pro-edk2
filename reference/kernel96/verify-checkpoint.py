from pathlib import Path,PurePosixPath
import hashlib,json,re,tarfile
out=Path('/mnt/e/edk2-samurai-out/kernel96');ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel96')
sha=lambda b:hashlib.sha256(b).hexdigest()
def archive(p,root):
    files={}
    with tarfile.open(p) as t:
        for m in t:
            if not m.isfile():continue
            name=PurePosixPath(m.name);assert name.parts[0]==root and '..' not in name.parts
            name=str(PurePosixPath(*name.parts[1:]));assert name not in files
            files[name]=t.extractfile(m).read()
    names=set()
    for line in files['SHA256SUMS'].decode().splitlines():
        digest,name=line.split('  ',1);name=name.removeprefix('./')
        assert name not in names and name in files and sha(files[name])==digest;names.add(name)
    assert names==files.keys()-{'SHA256SUMS'}
    return files
files=archive(out/'checkpoint-final.tar','k96-checkpoint-final')
before=archive(out/'preflash.tar','k96-preflash')
state=files['state.txt'].decode();assert '#95 SMP PREEMPT' in state
assert state.splitlines()[3]=='0' and state.splitlines()[4]=='running'
assert b'0\n'==files['boot-finished']
assert 'WIFI_BOOTSTRAP_FINISHED result=0' in files['samurai-bluetooth-boot.log'].decode()
assert 'BT_DRIVER_REGISTERED' in files['samurai-bluetooth-boot.log'].decode()
assert b'wpa_state=COMPLETED\n' in files['wpa-status.txt'] and b'freq=5180\n' in files['wpa-status.txt']
assert all(x.endswith(': OK') for x in files['nv-source-check.txt'].decode().splitlines())
assert len(files['nv-source-check.txt'].decode().splitlines())==6
assert files['services/nv-source-hashes.txt']==before['nv-source-hashes.txt']
assert files['persist-check.txt']==b'/dev/sda2: OK\n'
addresses={}
for kind in ('bt','wlan'):
    mac=files[f'queries/k96-verified-{kind}-mac-le.bin'];raw=files[f'queries/k96-verified-{kind}-dms-response.bin']
    assert len(mac)==6 and any(mac) and any(x!=255 for x in mac) and not(mac[5]&3)
    assert len(raw)==24 and raw[:18]==bytes.fromhex('0201005c0011000204000000000010070006') and raw[18:]==mac
    assert mac==before[f'queries/k96-verified-{kind}-mac-le.bin'];addresses[kind]=mac
assert bytes.fromhex(files['wlan-address.txt'].decode().strip().replace(':',''))==addresses['wlan'][::-1]
assert files['tests/k96-initial/wlan-address-before.txt']!=files['tests/k96-initial/wlan-address-after.txt']
def bt_address(name):
    lines=files[name].decode().splitlines()
    line=next(x for x in lines if x.startswith('command=0x0004 status=0x00 payload='))
    assert bytes.fromhex(line.split('payload=')[1])[:6]==addresses['bt']
for name in ('bt-info.txt','tests/k96-initial-retry1/bt-powered-info.txt','tests/k96-hot-cycle/bt-offline-configured.txt','tests/k96-hot-cycle/bt-recovered-powered-info.txt'):bt_address(name)
readback=files['deployment-readback.txt'].decode()
candidate=json.loads((out/'candidate-validation.json').read_text())
for digest in (candidate['boot_sha256'],candidate['full_backup_boot_sha256'],candidate['logdump_sha256'],sha((ref/'samurai-bluetooth').read_bytes()),sha((out/'init-after').read_bytes()),sha((out/'dms-mac-read-verified').read_bytes()),sha((out/'bt-mgmt-probe').read_bytes())):
    assert digest in readback
for module in ('btbcm','btqca','hci_uart'):assert sha((out.parent/f'kernel94/{module}.ko').read_bytes()) in readback
assert 'BT_SCAN_WITH_MPSS_OFFLINE_PASS' in files['tests/k96-hot-cycle.log'].decode()
assert 'WIFI_RECOVERY_AFTER_INDEPENDENT_BT_PASS' in files['tests/k96-hot-cycle.log'].decode()
assert 'HOT_CYCLE_RECOVERY_PASS' in files['tests/k96-hot-cycle.log'].decode()
def scans(data):
    text=data.decode();assert 'command=0x0023 status=0x00' in text and 'discovering=0' in text
    records=re.findall(r'address=([0-9A-F:]+) type=(\d+)',text);assert records
    return len(set(records))
scan_counts={'mpss_offline':scans(files['tests/k96-hot-cycle/bt-offline-scan.txt'])}
displays={}
for phase in ('initial-retry1','recovery','five-ghz'):
    log=files[f'tests/k96-{phase}-coexistence.log'].decode()
    assert 'COEXISTENCE_OBSERVATION_PASS' in log
    samples=re.findall(r'^sample=(\d+) uptime=([\d.]+) MPSS=running WPA=COMPLETED DRM=present taint=0$',log,re.M)
    assert [int(x[0]) for x in samples]==list(range(1,46))
    vals=[]
    for suffix in ('before','after'):
        text=files[f'tests/k96-{phase}-coexistence/display-{suffix}.txt'].decode()
        assert re.search(r'underrun:\s*0\b',text)
        vals.append(int(re.search(r'vsync:\s*(\d+)',text)[1]))
    assert vals[1]>vals[0];displays[phase]=vals
    scan_counts[phase]=scans(files[f'tests/k96-{phase}-coexistence/bt-scan.txt'])
traffic={};internet={}
for phase in ('initial','recovery','five-ghz'):
    log=files[f'tests/k96-{phase}-network.log'].decode()
    for marker in ('GATEWAY_PING=PASS','DNS_LOOKUP=PASS','HTTP_FETCH=PASS','NETWORK_OBSERVATION_PASS'):assert marker in log
    internet[phase]=re.search(r'INTERNET_PING=(PASS|FAIL)',log)[1]
    # The first listener attempt was never launched because DHCP was not yet run.
    suffix='-retry1' if phase=='initial' else ''
    log=files[f'tests/k96-{phase}-traffic-server{suffix}.log'].decode()
    assert 'WIFI_TX_BYTES=4194304' in log and 'WIFI_RX_BYTES=4194304' in log
    sums=files[f'tests/k96-{phase}-traffic-sha.txt'].decode().splitlines()
    paths=[out/f'traffic-{phase}/traffic-download.bin',out/f'traffic-{phase}/traffic-upload-source.bin']
    vals=[]
    for line,p in zip(sums,paths):
        assert p.stat().st_size==4194304
        digest=line.split()[0];assert sha(p.read_bytes())==digest;vals.append(digest)
    assert len(vals)==2;traffic[phase]=vals
nfc=files['tests/k96-initial-retry1/nfc-controller.txt'].decode()
assert nfc.count('result=0 OK')==4 and 'powered=1' in nfc
dmesg=files['dmesg.txt'].decode()
for forbidden in ('failed to assign msa map permissions','failed to unmap msa permissions','TLV tx timeout','Fatal error received','frame done timeout'):
    assert forbidden not in dmesg,forbidden
report=dict(evidence_audit_pass=True,kernel_build=95,verified_private_files=len(files)-1,
    checkpoint_sha256=sha((out/'checkpoint-final.tar').read_bytes()),deployment_readback_verified=True,
    nv_and_persist_unchanged=True,dms_addresses_cross_boot_equal=True,runtime_wlan_and_bt_addresses_verified=True,
    automatic_address_provisioning=False,bt_pairing_connection_tested=False,cold_power_boot_tested=False,
    nfc_controller_only=True,hot_cycle_recovery_pass=True,coexistence_samples_per_phase=45,
    scan_address_type_counts=scan_counts,display_vsync_windows=displays,traffic_sha256=traffic,
    internet_ping_results=internet,bt_baudrate_retry_count=dmesg.count('Failed to change controller baudrate'),
    bt_frame_reassembly_error_count=dmesg.count('Frame reassembly failed'),goal_complete=False)
(out/'checkpoint-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
