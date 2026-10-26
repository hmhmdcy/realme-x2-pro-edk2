from pathlib import Path
import json
import subprocess
import os
assert os.geteuid()==0
dest=Path('/var/lib/samurai/k135-rollback-health')
assert dest.is_dir() and not (dest/'health-private.json').exists()
boot=Path('/var/lib/samurai/k135-rollback132-final/boot-id-private.txt').read_text().strip()
assert boot==Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
for name in ['phosh','phoc']:
    expected=Path('/var/lib/samurai/k135-rollback132-final/'+name+'.txt').read_text().strip()
    assert subprocess.check_output(['pgrep','-x',name],timeout=10).decode().strip()==expected
wifi=[dest/f'wifi-{i}-private.txt' for i in range(8)]
assert all(p.is_file() and 'freq: 5180' in p.read_text() for p in wifi)
span=wifi[-1].stat().st_mtime-wifi[0].stat().st_mtime
assert 42<=span<65
def counts(text):
    return {name:text.count(token) for name,token in [('dpu','frame done timeout'),('gpu','*** gpu fault'),('warn','WARNING:'),('codec_enospc','ASoC error (-28)'),('uart','reassembly failed')]}
before=counts((dest/'dmesg-before-private.txt').read_text())
after=counts((dest/'dmesg-after-private.txt').read_text())
assert before==after
checks=[]
for path,n in [('/run/samurai-wifi/nv-source-hashes.txt',6),('/var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256',4),('/var/lib/samurai/k115-vendor-camera-source/vendor-before.sha256',1)]:
    text=subprocess.check_output(['sha256sum','-c',path],timeout=90).decode()
    assert text.count(': OK')==n and 'FAILED' not in text
    checks.append(text)
(dest/'sources-check-private.txt').write_text(''.join(checks))
power=Path('/sys/class/power_supply/mp2650-input/uevent').read_text()
assert 'POWER_SUPPLY_ONLINE=1\n' in power
(dest/'mp2650-final-uevent.txt').write_text(power)
(dest/'boot-id-private.txt').write_text(boot+'\n')
report=dict(stage=135,current_kernel=132,guarded_samples=8,wifi_timestamp_span_seconds=span,same_boot_and_desktop_pids=True,taint=0,bluez_started=True,wifi_5180=True,slpi_offline_and_power_zero=True,nv6_source4_vendor1_preserved=True,fault_counts_before=before,fault_counts_after=after,fault_increments_zero=True,initial_source_hash_observation_timed_out=True,resumed_only_unexecuted_checksum_and_finalize_phase=True,standard_mp2650_uevents_persisted=1,mp2650_online_one=True,voltage_and_current_time_series_not_persisted=True,continuous_display_acceptance=False,gpu_load_test_performed=False,charging_control_accepted=False,goal_complete=False)
(dest/'health-private.json').write_text(json.dumps(report,indent=2)+'\n')
subprocess.run(['tar','-C',str(dest),'-czf','/tmp/k135-rollback-health-private.tar.gz','.'],check=True)
print('K135_EXISTING_HEALTH_WINDOW_REMAINING_HASH_CHECKS_AND_FINALIZE_COMPLETE',flush=True)
