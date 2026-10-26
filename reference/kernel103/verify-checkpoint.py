from pathlib import Path
import hashlib,json,re
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel103';out=Path('/mnt/e/edk2-samurai-out/kernel103')
namespace={};exec((ref/'verify-tests.py').read_text().split("runtime=archive(",1)[0],namespace)
archive=namespace['archive'];sha=namespace['sha']
files=archive('checkpoint-retry2.tar','k103-checkpoint-retry2')
for name,prefix in [('audio-runtime-retry1.tar','k103-audio-runtime-retry1'),('playback.tar','k103-playback'),
 ('capture.tar','k103-capture'),('capture-dmic0.tar','k103-capture-dmic0'),('auto-network.tar','k103-auto-network'),('core-rebind-once.tar','k103-core-rebind-once')]:
    original=archive(name,prefix)
    assert {n.removeprefix('tests/'+prefix+'/'):b for n,b in files.items() if n.startswith('tests/'+prefix+'/')}==original
state=files['state.txt'].decode().splitlines()
assert '#102 SMP PREEMPT' in state[0]
assert state[1]==(out/'runtime-boot-id-after-private.txt').read_text(encoding='utf-8-sig').strip()
assert state[3:]==['0','modem','running','adsp','running']
assert files['pcm-closed.txt']==b'closed\nclosed\n'
for l in files['amp-status.txt'].decode().splitlines():assert re.search(r'id=43 .*global=00 amp=80 .*powered=0 muted=1 starts=1 stops=1 failed=0$',l),l
assert files['bt-class.txt']==b''
assert b'freq=5180\n' in files['wifi-status.txt'] and b'wpa_state=COMPLETED\n' in files['wifi-status.txt']
assert len(files['nv-source-check.txt'].splitlines())==6 and all(l.endswith(b': OK') for l in files['nv-source-check.txt'].splitlines())
assert files['persist-stock-dtbo.sha']==files['tests/k103-audio-runtime-retry1/persist-stock-dtbo.sha']
assert re.search(rb'^id=97 go=00 state=00 .*active=0 starts=0 stops=0 watchdog_stops=0 error=0\n$',files['haptics-status.txt'])
tests=json.loads((out/'tests-validation.json').read_text());candidate=json.loads((out/'candidate-validation.json').read_text())
deployment={n:h for h,n in (l.split('  ',1) for l in files['deployment.sha'].decode().splitlines())}
assert deployment['/dev/sde11']==tests['full_boot_readback_sha256'] and deployment['/dev/sde32']==candidate['logdump_sha256']
init=Path('/home/cy122/x2pro-linux/initramfs')
for n,h in deployment.items():
    if n.startswith('/usr/') or n.startswith('/lib/') or n=='/init':assert sha((init/n.removeprefix('/')).read_bytes())==h
ns={};exec((root/'reference/kernel93/verify-firmware.py').read_text().split('\ndt_audit=')[0],ns)
exec((root/'reference/kernel73/dtb-canonical.py').read_text(),ns)
a=ns['canonical'](ns['fdt_nodes']((out/'dtb-audio').read_bytes()));b=ns['canonical'](ns['fdt_nodes'](files['runtime-fdt.bin']))
assert not a.keys()-b.keys() and b.keys()-a.keys()<= {'/chosen/boot-handoff'}
allowed={'linux,uefi-mmap-desc-size','linux,uefi-mmap-desc-ver','linux,uefi-mmap-size','linux,uefi-mmap-start','linux,uefi-system-table'}
diff={p:sorted(n for n in a[p].keys()|b[p].keys() if a[p].get(n)!=b[p].get(n)) for p in a if a[p]!=b[p]}
assert all(p=='/chosen' and set(v)<=allowed for p,v in diff.items()),diff
for n in allowed:assert int(b['/chosen'][n],16)>0
assert int(b['/chosen']['linux,uefi-mmap-desc-ver'],16)==1
assert int(b['/chosen']['linux,uefi-mmap-size'],16)%int(b['/chosen']['linux,uefi-mmap-desc-size'],16)==0
log=files['dmesg.txt'].decode()
assert not re.search(r'4080000\.remoteproc: fatal|17300000\.remoteproc: fatal|Unhandled context fault|unhandled context fault|Unexpected global fault|Kernel panic|Oops:',log)
up=float(re.search(r'\[\s*([\d.]+)\] remoteproc remoteproc0: remote processor modem is now up',log)[1])
report=dict(checkpoint_archive_audit_pass=True,stage=103,kernel_build=102,private_files_verified=len(files)-1,
 archive_sha256=sha((out/'checkpoint-retry2.tar').read_bytes()),uptime_seconds=float(state[2].split()[0]),mpss_running_seconds=float(state[2].split()[0])-up,
 first_automatic_wifi_start_pass=True,manual_mpss_recovery_executed=False,automatic_boot_profile_built_in=False,
 wifi_5g_auth_dhcp_dns_http_pass=True,wifi_stability_fixed=False,gateway_sent=3,gateway_received=3,
 native_alsa_card_registered=True,correct_dual_max98937_bound=True,revision='0x43',finite_pcm_playback_pass=True,
 amps_idle_global_zero=True,amp_start_stop_balanced=True,capture_dma_pass=True,microphone_signal_pass=False,capture_all_zero_twice=True,
 oem_handset_route='DMIC0/DEC5/SLIM_TX5',dmic_micbias_card_routes_missing=True,
 physical_speaker_sound_confirmed=False,microphone_quality_confirmed=False,headphone_or_jack_tested=False,
 native_api_query_pass=False,native_api_rebind_retry_count=1,native_api_failure_cause_unproven=True,no_dsp_restarts=True,
 bluetooth_controller_removed=True,bluetooth_pair_or_connect=False,motor_standby=True,physical_vibration_deferred_by_user=True,
 firmware_and_runtime_fdt_match=True,uefi_runtime_metadata_differences=diff,cpio_and_modules_preserved=True,nv_and_persist_preserved=True,
 kernel_taint=0,display_timeouts=log.count('frame done timeout'),bt_phase2_errors=log.count('Frame reassembly failed'),fatal_mpss=0,fatal_adsp=0,goal_complete=False)
(out/'checkpoint-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
