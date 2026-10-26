from pathlib import Path
import hashlib,json,re,tarfile
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel130';out=Path('/mnt/e/edk2-samurai-out/kernel130')
archive=out/'warmboot-private.tar.gz'
with tarfile.open(archive) as tf:d={m.name.removeprefix('./'):tf.extractfile(m).read() for m in tf if m.isfile()}
checked=set()
for line in d['SHA256SUMS'].decode().splitlines():
 h,n=line.split('  ',1);n=n.removeprefix('./');assert n not in checked and hashlib.sha256(d[n]).hexdigest()==h;checked.add(n)
assert checked==d.keys()-{'SHA256SUMS'}
assert d['boot-id-private.txt'].strip()==(out/'embedded-boot-id-private.txt').read_bytes().strip() and d['boot-id-private.txt'].strip()!=(out/'source-boot-id-private.txt').read_bytes().strip()
result=json.loads(d['result.json']);assert all(result[k] for k in ['new_warm_boot_same_kernel129','automatic_openrc_bluez_and_fresh_dms_address_ready','no_manual_service_activation_or_address_provision_after_reboot','service_running'])
assert not result['controller_final_powered'] and not result['discovery_final_off'] is False
assert d['default-service.txt']==b'/etc/init.d/bluetooth\n' and d['bluetooth-service']==(ref/'bluetooth').read_bytes()
assert b'\nAutoEnable=false\n' in d['main.conf-private'] and b'status: started' in d['service-status.txt']
assert b'RADIO_ADDRESS_QUERY_VERIFIED kind=bt' in d['startup-address-private.txt'] and b'BT_ADDRESS_VERIFIED index=0 powered=0 connectable=0 bondable=0' in d['startup-address-private.txt'] and b'BT_ADDRESS_READY' in d['startup-address-private.txt']
assert d['startup-radio.txt']==b'0\n'
values=[v for n,v in d.items() if n.startswith('radio-address-private/') and n.endswith('/bt-mac-le.bin')];assert len(values)==1;address=values[0]
boot_ids=[v for n,v in d.items() if n.startswith('radio-address-private/') and n.endswith('/boot-id')];assert boot_ids and all(v==d['boot-id-private.txt'] for v in boot_ids)
initial=json.loads(d['mgmt-initial-private.json']);final=json.loads(d['mgmt-final-private.json'])
assert initial['configured']==final['configured']==[0] and initial['unconfigured']==final['unconfigured']==[]
assert initial['info']['address_le']==final['info']['address_le']==address.hex() and not initial['info']['settings']&1 and not final['info']['settings']&1
for i in range(6):
 p=json.loads(d[f'adapter-{i}-private.json']);assert not p['Powered'] and not p['Discovering'] and p['Address'].lower()==':'.join(f'{x:02x}' for x in address[::-1])
 assert re.search(rb'freq: 5180(?:[.]0)?\s',d[f'wifi-link-{i}-private.txt'])
samples=json.loads(d['samples.json']);duration=samples[-1]['monotonic']-samples[0]['monotonic'];assert len(samples)==6 and duration>=50
assert all(x['taint']==0 and x['same_gui'] and x['radio_audio_running'] and x['bluetooth_service_running'] and not x['controller_powered'] and not x['discovering'] for x in samples)
assert d['wifi-profile-private.nmconnection']==(out.parent/'kernel128/wifi-dual-band-candidate-private.nmconnection').read_bytes()
assert re.search(rb'3 packets transmitted, 3 (?:packets )?received, 0% packet loss',d['gateway-private.txt'])
https=d['https-result.txt'].decode().split();assert https[0]=='200' and int(https[1])==len(d['https-body.txt'])>0
for name,count in [('nv-check.txt',6),('source-check.txt',4),('vendor-check.txt',1)]:assert d[name].count(b': OK')==count and b'FAILED' not in d[name]
assert d['module-check.txt'].count(b': OK')>=770 and b'FAILED' not in d['module-check.txt']
package=json.loads((r/'reference/kernel129/boot-package-validation.json').read_text());parts={n:h for h,n in (l.split('  ',1) for l in d['partitions.sha256'].decode().splitlines())}
assert parts['/dev/sde11']==package['boot_sha256'] and parts['/dev/sde32']==package['logdump_sha256'] and parts['/dev/sda2']=='7e085ef3264e212da7009099113b86ad1f6ec44176840f03f9b85d0e632412f3'
assert d['taint.txt']==b'0\n' and d['console-node.txt']==b'character special file 600 5 1 0 0\n'
assert d['sensor.txt']==b'offline\nvdd=0 vddio=0\n' and d['pcm.txt']==b'closed\nclosed\n' and d['amps.txt'].count(b'powered=0 muted=1')==2 and d['amps.txt'].count(b'failed=0')==2
before=d['dmesg-before.txt'];after=d['dmesg-after.txt'];assert after.startswith(before);new=after[len(before):].decode()
faults=['Frame reassembly failed','QCA Failed','tx timeout','firmware crashed','failed to remove peer key','timed out waiting peer','frame done timeout','*** gpu fault','Unhandled context fault','WARNING:','BUG:','Oops:'];counts={f:new.count(f) for f in faults};assert all(v==0 for v in counts.values())
assert b'unable to open an initial console' not in after
report=dict(stage=130,current_kernel=129,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),private_files_verified=len(checked),actual_new_warm_boot=True,
 no_manual_bt_service_activation_address_provision_or_wifi_activation=True,standard_openrc_bluez_auto_start_pass=True,fresh_same_boot_dms_identity_and_mgmt_dbus_readback_pass=True,
 service_default_runlevel_and_autoenable_false_persistent=True,bluetooth_service_running_controller_off=True,wifi_autonomous_5180_gateway3_https200_pass=True,
 https_bytes=len(d['https-body.txt']),samples=6,duration_seconds=duration,same_gui_radio_audio_taint0=True,initial_console_warning_count=0,
 total_boot_uart_reassembly_errors=after.count(b'Frame reassembly failed'),new_fault_counts=counts,total_dpu_timeouts=after.count(b'frame done timeout'),total_gpu_faults=after.count(b'*** gpu fault'),drm_active_crtc_count=d['drm-state.txt'].count(b'active=1'),
 source11_modules770_partitions_and_wifi_profile_preserved=True,sensor_power_and_audio_idle=True,pairing_transfer_physical_coldboot_suspend_longrun_not_claimed=True,goal_complete=False)
(ref/'warmboot-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
