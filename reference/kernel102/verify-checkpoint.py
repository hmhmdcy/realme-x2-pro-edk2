from pathlib import Path,PurePosixPath
import hashlib,json,re,tarfile
root=Path('/mnt/e/RealmeX2Pro edk2');out=Path('/mnt/e/edk2-samurai-out/kernel102')
sha=lambda b:hashlib.sha256(b).hexdigest()
def archive(path,prefix):
    files={}
    with tarfile.open(path) as tar:
        for m in tar:
            if not m.isfile():continue
            parts=PurePosixPath(m.name).parts
            assert parts[0]==prefix and '..' not in parts
            name=str(PurePosixPath(*parts[1:]));assert name not in files
            files[name]=tar.extractfile(m).read()
    checked=set()
    for line in files['SHA256SUMS'].decode().splitlines():
        digest,name=line.split('  ',1);name=name.removeprefix('./')
        assert name not in checked and sha(files[name])==digest
        checked.add(name)
    assert checked==files.keys()-{'SHA256SUMS'}
    return files
files=archive(out/'checkpoint.tar','k102-checkpoint')
audio=archive(out/'audio-runtime-retry1.tar','k102-audio-runtime-retry1')
net=archive(out/'auto-network-completion.tar','k102-auto-network-completion')
amps=archive(out/'amp-readonly-ids.tar','k102-amp-readonly-ids')
for name,original in [('k102-audio-runtime-retry1',audio),('k102-auto-network-completion',net),('k102-amp-readonly-ids',amps)]:
    assert {p.removeprefix('tests/'+name+'/'):b for p,b in files.items() if p.startswith('tests/'+name+'/')}==original
assert files['result.txt']==b'WCD934X_AND_DUAL_MAX98937_IDS_AUTO_WIFI_CHECKPOINT_PASS\n'
assert files['boot-finished']==audio['boot-finished']==b'0\n'
assert files['samurai-wifi-boot.log']==audio['samurai-wifi-boot.log']
assert files['samurai-bluetooth-boot.log']==audio['samurai-bluetooth-boot.log']
state=files['state.txt'].decode().splitlines()
assert '#101 SMP PREEMPT' in state[0] and state[1]==(out/'runtime-boot-id-after-private.txt').read_text().strip()
assert state[3:] == ['0','running','running']
assert files['native-api.txt']==audio['native-api-reply.txt']==b'native_version_reply service4_api=7 service4_branch=0 service7_api=2 service7_branch=0\n'
assert b'--- no soundcards ---' in files['alsa-cards.txt']
assert b'wcd934x-codec.0.auto\n' in files['codec-components.txt'] and b'max98927' not in files['codec-components.txt']
assert amps['id-replies.txt']==b'address=0x39 rev_01ff=0x00 rev_0600=0x43\naddress=0x3a rev_01ff=0x00 rev_0600=0x43\n'
assert amps['id-error.txt']==b''
assert re.search(rb'gpio37\s+: out low',files['gpio.txt']) and re.search(rb'gpio148\s+: out low',files['gpio.txt'])
assert 'pin 54 (GPIO_54): device 4-0020 function gpio group gpio54' in files['pinmux.txt'].decode()
assert b'freq=5180\n' in files['wifi-status.txt'] and b'wpa_state=COMPLETED\n' in files['wifi-status.txt']
assert files['bt-class.txt']==net['bt-class.txt']==b''
assert b'3 packets transmitted, 3 packets received, 0% packet loss' in net['original-network-partial/gateway.txt']
assert len(net['original-network-partial/http.txt'])==577 and b'Example Domain' in net['original-network-partial/http.txt']
assert b'FAIL\n' not in net['original-network-partial/reconfigure.txt']
assert net['result.txt']==b'AUTO_BOOT_5G_AUTH_DHCP_GATEWAY_DNS_HTTP_PASS\n'
assert len(files['nv-source-check.txt'].splitlines())==6 and all(l.endswith(b': OK') for l in files['nv-source-check.txt'].splitlines())
assert files['persist-after.sha'].decode().split()[0]==(out/'persist-before.sha').read_text().split()[0]
dep={name:digest for digest,name in (line.split('  ',1) for line in files['deployment.sha'].decode().splitlines())}
candidate=json.loads((out/'candidate-validation.json').read_text());runtime=json.loads((out/'runtime-validation.json').read_text())
assert dep['/dev/sde11']==runtime['full_boot_readback_sha256'] and dep['/dev/sde32']==candidate['logdump_sha256']
init=Path('/home/cy122/x2pro-linux/initramfs')
for name,digest in dep.items():
    if name.startswith('/usr/') or name.startswith('/lib/') or name=='/init': assert sha((init/name.removeprefix('/')).read_bytes())==digest
assert re.search(rb'^id=97 go=00 state=00 .*active=0 starts=0 stops=0 watchdog_stops=0 error=0\n$',files['haptics-status.txt'])
ns={}
exec((root/'reference/kernel93/verify-firmware.py').read_text().split('\ndt_audit=')[0],ns)
exec((root/'reference/kernel73/dtb-canonical.py').read_text(),ns)
a=ns['canonical'](ns['fdt_nodes']((out/'dtb-audio').read_bytes()))
b=ns['canonical'](ns['fdt_nodes'](files['runtime-fdt.bin']))
expected_added={'/chosen/boot-handoff'}
assert b.keys()-a.keys()<=expected_added and not a.keys()-b.keys()
allowed={'/chosen':['linux,uefi-mmap-desc-size','linux,uefi-mmap-desc-ver','linux,uefi-mmap-size','linux,uefi-mmap-start','linux,uefi-system-table']}
differences={p:sorted(n for n in a[p].keys()|b[p].keys() if a[p].get(n)!=b[p].get(n)) for p in a if a[p]!=b[p]}
assert all(p in allowed and set(keys)<=set(allowed[p]) for p,keys in differences.items()),differences
for n in allowed['/chosen']:assert int(b['/chosen'][n],16)>0,n
assert int(b['/chosen']['linux,uefi-mmap-desc-ver'],16)==1
assert int(b['/chosen']['linux,uefi-mmap-size'],16)%int(b['/chosen']['linux,uefi-mmap-desc-size'],16)==0
dmesg=files['dmesg.txt'].decode()
fatal_mpss=len(re.findall(r'4080000\.remoteproc: fatal',dmesg));fatal_adsp=len(re.findall(r'17300000\.remoteproc: fatal',dmesg))
assert fatal_mpss==fatal_adsp==0
assert not re.search('unhandled context fault|Unhandled context fault|Unexpected global fault',dmesg)
up=float(re.search(r'\[\s*([\d.]+)\] remoteproc remoteproc0: remote processor modem is now up',dmesg)[1])
report=dict(checkpoint_archive_audit_pass=True,logical_stage=102,kernel_build=101,verified_private_files=len(files)-1,
 checkpoint_sha256=sha((out/'checkpoint.tar').read_bytes()),uptime_seconds=float(state[2].split()[0]),
 mpss_running_seconds=float(state[2].split()[0])-up,automatic_wifi_start_pass=True,automatic_boot_tested_count=1,
 automatic_connection_profile_built_in=False,manual_mpss_recovery_executed=False,fatal_mpss=fatal_mpss,fatal_adsp=fatal_adsp,
 adsp_native_version_reply_pass=True,wcd_chip_major='0x108',wcd_chip_minor='0x1',wcd_codec_bound=True,
 actual_amp_model='MAX98937',amp_revision='0x43',amp_addresses=['0x39','0x3a'],amp_driver_mismatch_identified=True,
 wrong_amp_components_unbound=True,amp_resets_physical_low=True,amp_register_data_writes=False,
 alsa_cards_empty=True,alsa_output_tested=False,bluetooth_controller_removed=True,no_pair_or_connect=True,
 wifi_band_mhz=5180,gateway_sent=3,gateway_received=3,dns_http_pass=True,wifi_stability_fixed=False,
 initramfs_byte_identical=True,nv_unchanged=True,persist_unchanged=True,deployment_and_runtime_fdt_match=True,uefi_runtime_metadata_differences=differences,
 motor_standby=True,physical_vibration_confirmed=False,physical_vibration_deferred_by_user=True,
 kernel_taint=0,display_timeouts=dmesg.count('frame done timeout'),bt_frame_errors=dmesg.count('Frame reassembly failed'),
 key_deletion_instrumented_this_boot=False,goal_complete=False)
(out/'checkpoint-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
