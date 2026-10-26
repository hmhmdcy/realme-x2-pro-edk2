from pathlib import Path
import hashlib,json,re,tarfile
out=Path('/mnt/e/edk2-samurai-out/kernel94');archive=out.parent/'kernel95/preflash.tar'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='4e9488151d7edd289ef2176e947882b2d5f91577da277f34f1ee7a0f325d7f5e'
with tarfile.open(archive) as src:files={Path(m.name).name:src.extractfile(m).read() for m in src if m.isfile()}
for line in files['SHA256SUMS'].decode().splitlines():
    digest,name=line.split('  ',1);assert hashlib.sha256(files[name]).hexdigest()==digest
txt=lambda name:files[name].decode()
assert '#93 SMP PREEMPT' in txt('state.txt') and '\n0\nrunning\n' in txt('state.txt')
assert 'msmdrmfb frame buffer device' in txt('dmesg.txt')
assert 'boot CTL0 cleared' in txt('dmesg.txt')
assert 'fatal error' not in txt('dmesg.txt') and 'tx timeout' not in txt('dmesg.txt')
assert txt('samurai-wifi-boot.log')=='PREPARE_OK\nWIFI_READY\n'
assert 'BT_DRIVER_REGISTERED' in txt('samurai-bluetooth-boot.log')
assert '/sbin/insmod: not found' in txt('k94-bt-autoload-failed.log')
co=txt('k94-coexistence.log');assert co.count('MPSS=running WPA=COMPLETED DRM=present taint=0')==45 and 'COEXISTENCE_OBSERVATION_PASS' in co
scan=txt('k94-coexistence-scan.txt');assert 'command=0x0023 status=0x00' in scan and 'discovering=0' in scan
found=set(re.findall(r'address=([0-9A-Fa-f:]+) type=(\d+)',scan));assert found
assert txt('k94-nfc-controller.txt').count('result=0 OK')==4 and 'powered=1' in txt('k94-nfc-controller.txt')
assert len(txt('nv-source-check.txt').splitlines())==6 and all(line.endswith(': OK') for line in txt('nv-source-check.txt').splitlines())
assert txt('persist-check.txt').endswith(': OK\n')
vsync=[]
for name in ('k94-display-before-scan.txt','k94-display-after-scan.txt'):
    s=txt(name);vsync.append(int(re.search(r'vsync:\s*(\d+)',s)[1]));assert int(re.search(r'underrun:\s*(\d+)',s)[1])==0
assert vsync[1]>vsync[0]
assert 'freq=2462\n' in txt('wpa-status.txt') and 'wpa_state=COMPLETED\n' in txt('wpa-status.txt')
assert 'WIFI_TX_BYTES=4194304' in txt('k94-traffic-server.log') and 'WIFI_RX_BYTES=4194304' in txt('k94-traffic-server.log')
for name,digest in [('traffic-download.bin','5cc82a5dbaad21fba1ff8c9066c074d04a157b86cec0ca2a5328ea0789466289'),('traffic-upload-source.bin','a3307919b843877c99dc3ab3a7e0de21b09947e300cfdd02ca51bfc0193b9a9e')]:
    p=out/'traffic'/name;assert p.stat().st_size==4194304 and hashlib.sha256(p.read_bytes()).hexdigest()==digest
    assert digest in txt('k94-traffic-sha.txt')
report=dict(checkpoint_evidence_pass=True,private_files_verified=len(files)-1,kernel_build=93,
    first_mpss_start_stable=True,current_drm_registered=True,display_vsync_before_after=vsync,display_underrun=0,
    wifi_2ghz_auth_dhcp_tcp_pass=True,coexistence_samples=45,coexistence_seconds=90,bluetooth_scan_unique_address_types=len(found),
    bluetooth_tlv_timeout_count=0,bluetooth_pair_connect_tested=False,nfc_controller_pass=True,nfc_rf_tested=False,
    nv_sources_unchanged=6,persist_unchanged=True,taint=0,automatic_bt_load_failed_path=True,runtime_loader_correction_tested=True,
    fixed_loader_automatic_boot_verified=False,goal_complete=False)
(out/'runtime-checkpoint-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
