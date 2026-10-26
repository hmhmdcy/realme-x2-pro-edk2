from pathlib import Path
import hashlib, json, re, tarfile
out=Path('/mnt/e/edk2-samurai-out/kernel93')
archive=out/'checkpoint-final.tar'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='b96c71dbb8e24c90b1f542f6525781a579e5336d8136bde38cb1abf6fb964037'
with tarfile.open(archive) as src:files={Path(m.name).name:src.extractfile(m).read() for m in src if m.isfile()}
for line in files['SHA256SUMS'].decode().splitlines():
    digest,name=line.split('  ',1);assert hashlib.sha256(files[name]).hexdigest()==digest
txt=lambda name:files[name].decode()
assert '#92 SMP PREEMPT' in txt('state.txt')
assert '\n0\nrunning\n' in txt('state.txt')
assert 'DRM absent' in txt('state.txt')
assert txt('bt-firmware-name.txt')=='crnv21.bin\ncrbtfw21.tlv\n'
assert 'freq=5180\n' in txt('wpa-status.txt') and 'wpa_state=COMPLETED\n' in txt('wpa-status.txt')
assert 'FIVE_GHZ_AUTH_DHCP_PASS' in txt('k93-5ghz2-test.log')
assert 'lease of ' in txt('k93-5ghz2-dhcp.txt') and 'wlan0 DHCP lease applied' in txt('k93-5ghz2-dhcp.txt')
for result in ['GATEWAY_PING=PASS','DNS_LOOKUP=PASS','HTTP_FETCH=PASS']:assert result in txt('k93-5ghz-network-test.txt')
assert 'INTERNET_PING=FAIL' in txt('k93-5ghz-network-test.txt')
assert len(txt('nv-check.txt').splitlines())==6 and all(line.endswith(': OK') for line in txt('nv-check.txt').splitlines())
for prefix,folder,tx,rx in [('', 'traffic','65f77025a95f09749f7f624cbea45752fbec271597051a9cfb50416b1d5f745e','9e6f8c085eca078993e3018edbf3bb13cffe204278c2e926c5b15787004e2915'),('5ghz-','traffic-5ghz','1018012774d8faf94357238d08f057611359c8a1a48243046c5fe155cf77bf36','f913ba1673611933ab21dc26a37230eb603b7be72c978386fb33544a15750686')]:
    server=txt(f'k93-{prefix}traffic-server.log');hashes=txt(f'k93-{prefix}traffic-sha.txt')
    assert 'WIFI_TX_BYTES=4194304' in server and 'WIFI_RX_BYTES=4194304' in server
    assert tx in hashes and rx in hashes
    for name,expected in [('traffic-download.bin',tx),('traffic-upload-source.bin',rx)]:
        p=out/folder/name;assert p.stat().st_size==4194304 and hashlib.sha256(p.read_bytes()).hexdigest()==expected
co=txt('k93-coexistence.log');assert co.count('MPSS=running WPA=COMPLETED taint=0')==45 and 'COEXISTENCE_OBSERVATION_PASS' in co
scan=txt('k93-bt-scan-final.txt');assert 'command=0x0023 status=0x00' in scan and 'discovering=0' in scan
assert 'event=0x0012' in scan
assert txt('k93-nfc-controller.txt').count('result=0 OK')==4 and 'powered=1' in txt('k93-nfc-controller.txt')
candidate=json.loads((out/'candidate-validation.json').read_text())
assert candidate['boot_sha256'] in txt('deployment-readback.txt') and candidate['logdump_sha256'] in txt('deployment-readback.txt')
report=dict(checkpoint_pass=True,private_files_verified=len(files)-1,kernel_build=92,
    wifi_2ghz_auth_dhcp_tcp_pass=True,wifi_5ghz_auth_dhcp_gateway_dns_http_tcp_pass=True,
    both_directions_bytes=4194304,coexistence_samples=45,coexistence_duration_seconds=90,
    bluetooth_scan_pass=True,bluetooth_pair_connect_tested=False,temporary_bluetooth_identity_only=True,
    nfc_controller_pass=True,nfc_tag_rf_tested=False,nv_sources_unchanged=6,taint=0,
    boot_logdump_readback_pass=True,first_mpss_start_failed=True,bluetooth_initial_tlv_retries=2,
    current_drm_registered=False,display_boot_ctl_failure=-22,goal_complete=False)
(out/'checkpoint-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
