from pathlib import Path, PurePosixPath
import hashlib, json, re, tarfile

out=Path('/mnt/e/edk2-samurai-out/kernel99')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel99')
sha=lambda data: hashlib.sha256(data).hexdigest()
def archive(filename, root):
    files={}
    with tarfile.open(out/filename) as handle:
        for member in handle:
            if not member.isfile(): continue
            parts=PurePosixPath(member.name).parts
            assert parts[0]==root and '..' not in parts
            name=str(PurePosixPath(*parts[1:]));assert name not in files
            files[name]=handle.extractfile(member).read()
    checked=set()
    for line in files['SHA256SUMS'].decode().splitlines():
        digest,name=line.split('  ',1);name=name.removeprefix('./')
        assert name not in checked and sha(files[name])==digest
        checked.add(name)
    assert checked==files.keys()-{'SHA256SUMS'}
    return files

radio=archive('radio-ram-recovery.tar','k99-radio-ram-recovery')
network=archive('restored-network-retry1.tar','k99-restored-network-retry1')
life=archive('haptics-lifecycle.tar','k99-haptics-lifecycle')
assert radio['result.txt']==b'RADIO_RAM_RECOVERY_PASS\n' and radio['wifi-result.txt']==b'0\n'
assert radio['address-status.txt']==b'wlan_cache=verified-this-boot\nbt_cache=verified-this-boot\n'
assert 'BT_ADDRESS_VERIFIED index=0 powered=0 connectable=0 bondable=0' in radio['bt-start.txt'].decode()
assert 'WIFI_READY\n' in radio['wifi-start.txt'].decode()
assert radio['service-before']==(ref.parent/'kernel97/samurai-wifi').read_bytes()
assert sha((ref/'samurai-wifi').read_bytes()) in radio['service-hashes.txt'].decode()
assert len(radio['nv-check.txt'].decode().splitlines())==6
assert all(line.endswith(': OK') for line in radio['nv-check.txt'].decode().splitlines())
assert network['result.txt']==b'MANUAL_RECOVERY_5G_AUTH_DHCP_GATEWAY_DNS_HTTP_PASS\n'
assert network['reconfigure.txt']==b'OK\n'
assert 'wpa_state=COMPLETED\n' in network['status.txt'].decode() and 'freq=5180\n' in network['status.txt'].decode()
assert '0% packet loss' in network['gateway.txt'].decode()
assert len(network['http.txt'])==577 and b'Example Domain' in network['http.txt']
assert not re.search(r'CTRL-EVENT-DISCONNECTED.*reason=',network['wpa.log'].decode())
payload=bytes.fromhex(re.search(r'command=0x0004 status=0x00 payload=([0-9a-f]+)',network['bt-info.txt'].decode())[1])
assert len(payload)==280 and int.from_bytes(payload[13:17],'little')&0x1b==0
assert life['result.txt']==b'HAPTICS_CLOSE_KILL_WATCHDOG_PASS\n'
for mode, count, watchdog in (('close',4,0),('kill',5,0),('watchdog',6,1)):
    after=life[f'{mode}-after.txt'].decode()
    assert re.search(r'^id=97 go=00 state=00 .*active=0 ',after)
    assert f'starts={count} stops={count} watchdog_stops={watchdog} error=0\n' in after
    assert 'go=01 state=06 ' in life[f'{mode}-samples.txt'].decode()
samples=[]
for line in life['watchdog-samples.txt'].decode().splitlines():
    uptime=float(re.search(r'uptime=([\d.]+)',line)[1])
    samples.append((uptime,'active=1' in line,'watchdog_stops=1' in line))
start=min(t for t,active,wd in samples if active)
stop=min(t for t,active,wd in samples if wd and not active)
assert 0.80<=stop-start<=1.25
assert samples[-1][0]-start>=1.5 and samples[-1][2]
assert b'WATCHDOG_FD_STILL_OPEN_AFTER_1800MS\n' in life['watchdog.log']
assert life['state.txt'].decode().splitlines()[0]=='0'
assert life['dmesg-before.txt'].decode().count('frame done timeout')==life['dmesg-after.txt'].decode().count('frame done timeout')
report=dict(runtime_audit_pass=True, logical_stage=99, kernel_build=98,
    ram_radio_recovery_pass=True, readiness_fix_embedded_in_flash=False,
    manual_5ghz_auth_dhcp_gateway_dns_http_pass=True, automatic_ap_connection=False,
    bluetooth_powered=False, bluetooth_pairing_or_connection_tested=False,
    close_stops_haptics=True, sigkill_stops_haptics=True, watchdog_stops_haptics=True,
    watchdog_observed_seconds=round(stop-start,3), physical_vibration_confirmed=False,
    suspend_resume_tested=False,cold_power_boot_tested=False,goal_complete=False,
    private_archives={name:dict(sha256=sha((out/name).read_bytes()),files=len(files)-1) for name,files in
        [('radio-ram-recovery.tar',radio),('restored-network-retry1.tar',network),('haptics-lifecycle.tar',life)]})
(out/'runtime-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
