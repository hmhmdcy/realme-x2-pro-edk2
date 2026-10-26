from pathlib import Path
import hashlib,json,re,tarfile
out=Path('/mnt/e/edk2-samurai-out/kernel95');archive=out/'checkpoint-final.tar'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
with tarfile.open(archive) as src:files={Path(m.name).name:src.extractfile(m).read() for m in src if m.isfile()}
for line in files['SHA256SUMS'].decode().splitlines():
    digest,name=line.split('  ',1);assert hashlib.sha256(files[name]).hexdigest()==digest
txt=lambda name:files[name].decode()
assert '#94 SMP PREEMPT' in txt('state.txt') and '\n0\nrunning\n' in txt('state.txt')
assert 'boot CTL0 cleared' in txt('dmesg.txt') and 'msmdrmfb frame buffer device' in txt('dmesg.txt')
assert 'fatal error' not in txt('dmesg.txt') and 'tx timeout' not in txt('dmesg.txt')
assert txt('samurai-wifi-boot.log')=='PREPARE_OK\nWIFI_READY\n'
btlog=txt('samurai-bluetooth-boot.log');assert 'BT_DRIVER_REGISTERED' in btlog and 'not found' not in btlog
assert 'QCA setup on UART is completed' in txt('k95-bt-autoload-dmesg.txt')
for mod in ('btbcm','btqca','hci_uart'):assert re.search(r'^'+mod+r' ',txt('modules.txt'),re.M)
assert 'freq=5180\n' in txt('wpa-status.txt') and 'wpa_state=COMPLETED\n' in txt('wpa-status.txt')
assert 'FIVE_GHZ_AUTH_DHCP_PASS' in txt('k95-5ghz-test.log')
for token in ('GATEWAY_PING=PASS','DNS_LOOKUP=PASS','HTTP_FETCH=PASS'):assert token in txt('k95-5ghz-network-test.txt')
counts=[];vsync=[];traffic_hashes=[]
for prefix,folder in [('', 'traffic'),('5ghz-', 'traffic-5ghz')]:
    co=txt(f'k95-{prefix}coexistence.log');assert co.count('MPSS=running WPA=COMPLETED DRM=present taint=0')==45 and 'COEXISTENCE_OBSERVATION_PASS' in co
    scan=txt(f'k95-{prefix}coexistence-scan.txt');assert 'command=0x0023 status=0x00' in scan and 'discovering=0' in scan
    found=set(re.findall(r'address=([0-9A-Fa-f:]+) type=(\d+)',scan));assert found;counts.append(len(found))
    v=[]
    for moment in ('before','after'):
        s=txt(f'k95-{prefix}display-{moment}-scan.txt');v.append(int(re.search(r'vsync:\s*(\d+)',s)[1]));assert int(re.search(r'underrun:\s*(\d+)',s)[1])==0
    assert v[1]>v[0];vsync.append(v)
    server=txt(f'k95-{prefix}traffic-server.log');assert 'WIFI_TX_BYTES=4194304' in server and 'WIFI_RX_BYTES=4194304' in server
    values={}
    for name in ('traffic-download.bin','traffic-upload-source.bin'):
        p=out/folder/name;assert p.stat().st_size==4194304
        digest=sha(p);assert digest in txt(f'k95-{prefix}traffic-sha.txt');values[name]=digest
    traffic_hashes.append(values)
assert 'freq=2462\n' in txt('k95-2ghz-status.txt') and 'wpa_state=COMPLETED\n' in txt('k95-2ghz-status.txt')
assert txt('k95-nfc-controller.txt').count('result=0 OK')==4 and 'powered=1' in txt('k95-nfc-controller.txt')
assert len(txt('nv-source-check.txt').splitlines())==6 and all(line.endswith(': OK') for line in txt('nv-source-check.txt').splitlines())
with tarfile.open(out/'preflash.tar') as src:
    previous_nv=src.extractfile('k95-preflash/nv-source-hashes.txt').read().decode()
assert sorted(line.split()[0] for line in previous_nv.splitlines())==sorted(line.split()[0] for line in txt('nv-source-hashes.txt').splitlines())
assert txt('persist-check.txt').endswith(': OK\n')
c=json.loads((out/'candidate-validation.json').read_text())
for key in ('boot_sha256','logdump_sha256','full_backup_boot_sha256'):assert c[key] in txt('deployment-readback.txt')
for mod in ('btbcm','btqca','hci_uart'):
    assert sha(out.parent/'kernel94'/f'{mod}.ko') in txt('deployment-readback.txt')
assert sha(Path('/mnt/e/RealmeX2Pro edk2/reference/kernel95/samurai-bluetooth')) in txt('deployment-readback.txt')
report=dict(checkpoint_evidence_pass=True,archive_sha256=sha(archive),private_files_verified=len(files)-1,kernel_build=94,
    first_mpss_start_stable=True,bluetooth_automatic_module_load_pass=True,bluetooth_tlv_timeout_count=0,
    wifi_both_bands_auth_dhcp_tcp_pass=True,each_direction_bytes=4194304,traffic_hashes=traffic_hashes,
    coexistence_each_band_samples=45,coexistence_each_band_seconds=90,bluetooth_scan_unique_address_types=counts,
    bluetooth_pair_connect_tested=False,temporary_bluetooth_identity_only=True,nfc_controller_pass=True,nfc_rf_tested=False,
    current_drm_registered=True,display_vsync_before_after=vsync,display_underrun=0,
    nv_sources_unchanged=6,persist_unchanged=True,taint=0,boot_logdump_readback_pass=True,goal_complete=False)
(out/'checkpoint-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
