from pathlib import Path
import hashlib, json, re
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel104';out=Path('/mnt/e/edk2-samurai-out/kernel104')
ns={};exec((ref/'verify-tests.py').read_text().split("runtime=archive(",1)[0],ns)
archive=ns['archive'];sha=ns['sha']
files=archive('checkpoint.tar','k104-checkpoint')
names=['audio-runtime','playback','auto-network','first-boot-failure','radio-recovery-first','core-rebind-once']+[f'capture-dmic{n}' for n in range(3)]
for name in names:
    prefix='k104-'+name
    original=archive(name+'.tar',prefix)
    assert {n.removeprefix('tests/'+prefix+'/'):b for n,b in files.items() if n.startswith('tests/'+prefix+'/')}==original
state=files['state.txt'].decode().splitlines()
assert '#103 SMP PREEMPT' in state[0]
assert state[1]==(out/'runtime-boot-id-after-private.txt').read_text().strip()
assert state[3:]==['0','modem','running','adsp','running']
assert files['pcm-closed.txt']==b'closed\nclosed\n'
for l in files['amp-status.txt'].decode().splitlines():assert re.search(r'id=43 .*global=00 amp=80 .*powered=0 muted=1 starts=1 stops=1 failed=0$',l),l
assert files['bt-class.txt']==b''
assert b'freq=5180\n' in files['wifi-status.txt'] and b'wpa_state=COMPLETED\n' in files['wifi-status.txt']
assert len(files['nv-source-check.txt'].splitlines())==6 and all(l.endswith(b': OK') for l in files['nv-source-check.txt'].splitlines())
assert files['persist-stock-dtbo.sha']==files['tests/k104-audio-runtime/persist-stock-dtbo.sha']
assert re.search(rb'^id=97 go=00 state=00 .*active=0 starts=0 stops=0 watchdog_stops=0 error=0\n$',files['haptics-status.txt'])
tests=json.loads((out/'tests-validation.json').read_text());candidate=json.loads((out/'candidate-validation.json').read_text())
deployment={n:h for h,n in (l.split('  ',1) for l in files['deployment.sha'].decode().splitlines())}
assert deployment['/dev/sde11']==tests['full_boot_readback_sha256'] and deployment['/dev/sde32']==candidate['logdump_sha256']
init=Path('/home/cy122/x2pro-linux/initramfs')
for n,h in deployment.items():
    if n.startswith('/usr/') or n.startswith('/lib/') or n=='/init':assert sha((init/n.removeprefix('/')).read_bytes())==h
dt={};exec((root/'reference/kernel93/verify-firmware.py').read_text().split('\ndt_audit=')[0],dt)
exec((root/'reference/kernel73/dtb-canonical.py').read_text(),dt)
a=dt['canonical'](dt['fdt_nodes']((out/'dtb-audio').read_bytes()));b=dt['canonical'](dt['fdt_nodes'](files['runtime-fdt.bin']))
assert not a.keys()-b.keys() and b.keys()-a.keys()<= {'/chosen/boot-handoff'}
allowed={'linux,uefi-mmap-desc-size','linux,uefi-mmap-desc-ver','linux,uefi-mmap-size','linux,uefi-mmap-start','linux,uefi-system-table'}
diff={p:sorted(n for n in a[p].keys()|b[p].keys() if a[p].get(n)!=b[p].get(n)) for p in a if a[p]!=b[p]}
assert all(p=='/chosen' and set(v)<=allowed for p,v in diff.items()),diff
for n in allowed:assert int(b['/chosen'][n],16)>0
assert int(b['/chosen']['linux,uefi-mmap-desc-ver'],16)==1
assert int(b['/chosen']['linux,uefi-mmap-size'],16)%int(b['/chosen']['linux,uefi-mmap-desc-size'],16)==0
log=files['dmesg.txt'].decode()
assert log.count('4080000.remoteproc: fatal')==1
assert not re.search(r'17300000\.remoteproc: fatal|Unhandled context fault|unhandled context fault|Unexpected global fault|Kernel panic|Oops:',log)
ups=re.findall(r'\[\s*([\d.]+)\] remoteproc remoteproc\d+: remote processor modem is now up',log)
assert len(ups)==2,ups
up=float(ups[-1])
core_log=[l for l in log.splitlines() if 'samurai core' in l]
slim_log=[l for l in log.splitlines() if 'samurai slim trigger' in l]
report=dict(checkpoint_archive_audit_pass=True,stage=104,kernel_build=103,private_files_verified=len(files)-1,
 archive_sha256=sha((out/'checkpoint.tar').read_bytes()),uptime_seconds=float(state[2].split()[0]),mpss_running_seconds=float(state[2].split()[0])-up,
 first_automatic_wifi_start_pass=False,automatic_boot_failure_preserved=True,manual_mpss_recovery_executed=True,manual_mpss_recovery_count=1,
 wifi_5g_auth_dhcp_dns_http_pass=True,wifi_stability_fixed=False,gateway_sent=3,gateway_received=3,
 native_alsa_card_registered=True,correct_dual_max98937_bound=True,finite_pcm_playback_pass=True,
 amps_idle_global_zero=True,amp_start_stop_balanced=True,microphone_signal_pass=tests['microphone_signal_pass'],microphones=tests['microphones'],
 physical_speaker_sound_confirmed=False,microphone_quality_confirmed=False,headphone_or_jack_tested=False,
 native_api_query_pass=tests['native_api_query_pass'],native_api_reply=tests['native_api_reply'],
 actual_core_reply_diagnostics=core_log,actual_slim_trigger_diagnostics=slim_log,no_adsp_restarts=True,core_rebind_count=1,
 bluetooth_controller_removed=True,bluetooth_pair_or_connect=False,motor_standby=True,physical_vibration_deferred_by_user=True,
 firmware_and_runtime_fdt_match=True,uefi_runtime_metadata_differences=diff,cpio_and_modules_preserved=True,nv_and_persist_preserved=True,
 kernel_taint=0,display_timeouts=log.count('frame done timeout'),bt_phase2_errors=log.count('Frame reassembly failed'),fatal_mpss=1,fatal_adsp=0,goal_complete=False)
(out/'checkpoint-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({n:report[n] for n in ('checkpoint_archive_audit_pass','private_files_verified','archive_sha256','uptime_seconds','microphone_signal_pass','native_api_query_pass','display_timeouts','bt_phase2_errors','actual_core_reply_diagnostics','actual_slim_trigger_diagnostics')},indent=2))
