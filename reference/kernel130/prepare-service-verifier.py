from pathlib import Path
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel130'
s=(ref/'verify-discovery.py').read_text().replace("archive=out/'discovery-checkpoint-private.tar.gz'", "archive=out/'service-checkpoint-private.tar.gz'").replace("prefix='k130-bluez-discovery-r2/'", "prefix='k130-bluez-service-discovery/'")
s=s.replace("result['daemon_stopped']", "result['daemon_service_running'] and not result['daemon_stopped']")
a=s.index("initial=json.loads(d['k130-mgmt-before");b=s.index('initial_scan=json.loads',a)
s=s[:a]+'''with tarfile.open(out/'discovery-checkpoint-private.tar.gz') as tf:
 first={m.name.removeprefix('./'):tf.extractfile(m).read() for m in tf if m.isfile()}
provision_files=[v for n,v in first.items() if n.startswith('k130-address-provision/radio-address-private/') and n.endswith('/bt-mac-le.bin')];assert len(provision_files)==1
address=provision_files[0];assert len(address)==6
service='k130-live-bluez-service/'
assert d[service+'bluetooth-after']==(r/'reference/kernel130/bluetooth').read_bytes()
assert d[service+'main.conf-after-private']==d[service+'main.conf-before-private'].replace(b'#AutoEnable=true\\n',b'AutoEnable=false\\n')
assert d[service+'runlevel-link.txt']==b'/etc/init.d/bluetooth\\n'
for name in ['service-start-status.txt','service-restart-status.txt']:assert b'status: started' in d[service+name]
for name in ['address-start-private.txt','address-restart-private.txt']:assert b'BT_ADDRESS_VERIFIED index=0 powered=0 connectable=0 bondable=0' in d[service+name] and b'BT_ADDRESS_READY' in d[service+name]
for name in ['service-status-before.txt','service-status-after.txt']:assert b'status: started' in d[prefix+name]
'''+s[b:]
s=s.replace('initial_controller_missing_address=True','standard_openrc_address_startup_start_and_restart_pass=True,default_runlevel_enabled=True').replace('final_bluez_stopped=True','final_bluez_stopped=False,final_standard_bluez_service_running=True').replace('automatic_startup_integration_pending=True','startup_integration_deployed_actual_new_boot_verification_pending=True').replace("reference/kernel130/discovery-validation.json", "reference/kernel130/service-validation.json")
assert not (ref/'verify-service.py').exists();(ref/'verify-service.py').write_text(s)
print('K130_SERVICE_VERIFIER_PREPARED')
