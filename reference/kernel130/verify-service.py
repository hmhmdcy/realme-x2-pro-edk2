from pathlib import Path
import hashlib,json,re,struct,tarfile
r=Path('/mnt/e/RealmeX2Pro edk2');out=Path('/mnt/e/edk2-samurai-out/kernel130')
archive=out/'service-checkpoint-private.tar.gz'
with tarfile.open(archive) as tf: d={m.name.removeprefix('./'):tf.extractfile(m).read() for m in tf if m.isfile()}
verified=set()
for line in d['SHA256SUMS'].decode().splitlines():
 h,n=line.split('  ',1);n=n.removeprefix('./');assert n not in verified and hashlib.sha256(d[n]).hexdigest()==h;verified.add(n)
assert verified==d.keys()-{'SHA256SUMS'}
assert d['boot-id-private.txt'].strip()==(out.parent/'kernel129/embedded-boot-id-private.txt').read_bytes().strip()
assert d['taint.txt']==b'0\n'
prefix='k130-bluez-service-discovery/'
result=json.loads(d[prefix+'result.json']);assert result['pass_all'] and result['failure'] is None and not result['monitor_errors']
assert result['final_powered'] is False and result['daemon_service_running'] and not result['daemon_stopped'] and result['cleanup']==['discovery_off_power_off']
assert [x['transport'] for x in result['rounds']]==['le','bredr','auto']
for x in result['rounds']: assert x['discovery_started'] and x['discovery_stopped'] and x['duration_seconds']>=x['requested_seconds'] and not x['paired_connected_bonded']
with tarfile.open(out/'discovery-checkpoint-private.tar.gz') as tf:
 first={m.name.removeprefix('./'):tf.extractfile(m).read() for m in tf if m.isfile()}
provision_files=[v for n,v in first.items() if n.startswith('k130-address-provision/radio-address-private/') and n.endswith('/bt-mac-le.bin')];assert len(provision_files)==1
address=provision_files[0];assert len(address)==6
service='k130-live-bluez-service/'
assert d[service+'bluetooth-after']==(r/'reference/kernel130/bluetooth').read_bytes()
assert d[service+'main.conf-after-private']==d[service+'main.conf-before-private'].replace(b'#AutoEnable=true\n',b'AutoEnable=false\n')
assert d[service+'runlevel-link.txt']==b'/etc/init.d/bluetooth\n'
for name in ['service-start-status.txt','service-restart-status.txt']:assert b'status: started' in d[service+name]
for name in ['address-start-private.txt','address-restart-private.txt']:assert b'BT_ADDRESS_VERIFIED index=0 powered=0 connectable=0 bondable=0' in d[service+name] and b'BT_ADDRESS_READY' in d[service+name]
for name in ['service-status-before.txt','service-status-after.txt']:assert b'status: started' in d[prefix+name]
initial_scan=json.loads(d[prefix+'mgmt-initial-private.json']);final=json.loads(d[prefix+'mgmt-final-private.json'])
assert initial_scan['info']['address_le']==final['info']['address_le']==address.hex()
assert initial_scan['info']['settings'] & (1|2|8|16)==0 and final['info']['settings'] & 1==0
adapter_final=json.loads(d[prefix+'adapter-final-private.json']);assert not adapter_final['Powered'] and not adapter_final['Discovering']
powered=json.loads(d[prefix+'adapter-powered-private.json']);assert powered['Powered'] and all(not powered[k] for k in ('Pairable','Connectable','Discoverable'))
events=[json.loads(l) for l in d[prefix+'events-mgmt-private.jsonl'].decode().splitlines()]
found=[];discovery=[]
for e in events:
 if e['kind']!='event': continue
 p=bytes.fromhex(e['payload'])
 if e['event']==0x12:
  assert len(p)>=14 and len(p)==14+struct.unpack_from('<H',p,12)[0]
  found.append((p[:6],p[6],struct.unpack('b',p[7:8])[0]))
 if e['event']==0x13:
  assert len(p)==2;discovery.append(tuple(p))
assert found and any(t==0 for a,t,rssi in found) and any(t in (1,2) for a,t,rssi in found)
assert any(on for transport,on in discovery) and any(not on for transport,on in discovery)
hci=[json.loads(l) for l in d[prefix+'hci-monitor-private.jsonl'].decode().splitlines()]
commands=[];hci_events=[]
for record in hci:
 b=bytes.fromhex(record['packet']);assert len(b)>=6
 opcode,index,length=struct.unpack_from('<HHH',b);assert len(b)==6+length
 if opcode==2:
  assert len(b)>=9 and len(b)==9+b[8];commands.append(struct.unpack_from('<H',b,6)[0])
 elif opcode==3:
  assert len(b)>=8 and len(b)==8+b[7];hci_events.append(b[6])
assert 0x0401 in commands and (0x200c in commands or 0x2042 in commands)
assert 0x3e in hci_events
health=json.loads(d[prefix+'health.json']);assert len(health)>=22 and all(x['taint']==0 and x['frequency_mhz']==5180 and x['gui_same'] and x['radio_audio_running'] for x in health)
before=d[prefix+'dmesg-before.txt'];after=d[prefix+'dmesg-after.txt'];assert after.startswith(before)
new=after[len(before):].decode();faults=['Frame reassembly failed','QCA Failed','tx timeout','firmware crashed','failed to remove peer key','timed out waiting peer','frame done timeout','*** gpu fault','Unhandled context fault','WARNING:','BUG:','Oops:']
counts={f:new.count(f) for f in faults};assert all(v==0 for f,v in counts.items() if f!='Frame reassembly failed'); assert counts['Frame reassembly failed']==1; assert 'Frame reassembly failed (-84) phase=2 baud=115200 chunk=2 partial=0 first=00' in new and new.count('QCA setup on UART is completed')==1
for name,count in [('nv-check.txt',6),('source-check.txt',4),('vendor-check.txt',1)]:assert d[name].count(b': OK')==count and b'FAILED' not in d[name]
package=json.loads((r/'reference/kernel129/boot-package-validation.json').read_text());parts={n:h for h,n in (l.split('  ',1) for l in d['partitions.sha256'].decode().splitlines())}
assert parts['/dev/sde11']==package['boot_sha256'] and parts['/dev/sde32']==package['logdump_sha256'] and parts['/dev/sda2']=='7e085ef3264e212da7009099113b86ad1f6ec44176840f03f9b85d0e632412f3'
assert d['wifi-profile-private.nmconnection']==(out.parent/'kernel128/wifi-dual-band-candidate-private.nmconnection').read_bytes()
assert b'freq: 5180' in d['wifi-link-private.txt'] and d['radio-audio.txt']==b'running\nrunning\n'
report=dict(stage=130,current_kernel=129,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),private_files_verified=len(verified),
 standard_openrc_address_startup_start_and_restart_pass=True,default_runlevel_enabled=True,same_handset_readonly_dms_address_provisioned_and_readback_pass=True,
 standard_bluez587_dbus_le_bredr_auto_start_stop_pass=True,rounds=result['rounds'],
 mgmt_found_events=len(found),distinct_private_address_type_records=len(set((a,t) for a,t,rssi in found)),
 classic_and_le_actual_found_events=True,hci_packets=len(hci),actual_hci_inquiry_and_le_scan_commands=True,
 health_samples=len(health),scan_interval_seconds=health[-1]['monotonic']-health[0]['monotonic'],
 wifi5180_and_same_gui_radio_audio_preserved=True,new_fault_counts=counts,
 power_on_uart_reassembly_error_count=1,power_on_uart_recovered_setup_and_scan_pass=True,uart_reassembly_error_not_fixed=True,final_controller_powered=False,final_bluez_stopped=False,final_standard_bluez_service_running=True,
 original_source11_partitions_and_wifi_profile_preserved=True,startup_integration_deployed_actual_new_boot_verification_pending=True,
 pairing_transfer_coldboot_suspend_longrun_not_claimed=True,goal_complete=False)
(r/'reference/kernel130/service-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
