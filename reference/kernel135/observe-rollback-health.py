from pathlib import Path
import json
import subprocess
import time
import os
assert os.geteuid()==0
dest=Path('/var/lib/samurai/k135-rollback-health')
assert not dest.exists()
dest.mkdir(mode=0o700)
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot==Path('/var/lib/samurai/k135-rollback132-final/boot-id-private.txt').read_text().strip()
def cmd(args):
    return subprocess.check_output(args,timeout=10).decode()
assert cmd(['uname','-r']).strip()=='7.3.0-rc6-rmx1931-samurai-k132+'
pids=[cmd(['pgrep','-x',n]).strip() for n in ['phosh','phoc']]
assert all(pids)
def counts(text):
    return {name:text.count(token) for name,token in [('dpu','frame done timeout'),('gpu','*** gpu fault'),('warn','WARNING:'),('codec_enospc','ASoC error (-28)'),('uart','reassembly failed')]}
before=cmd(['dmesg'])
(dest/'dmesg-before-private.txt').write_text(before)
samples=[]
start=time.monotonic()
for i in range(8):
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==boot
    assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
    assert [cmd(['pgrep','-x',n]).strip() for n in ['phosh','phoc']]==pids
    assert Path('/sys/class/remoteproc/remoteproc0/state').read_text().strip()=='offline'
    assert Path('/sys/devices/platform/sensor-power/state').read_text().strip()=='vdd=0 vddio=0'
    assert 'started' in cmd(['rc-service','bluetooth','status'])
    wifi=cmd(['iw','dev','wlan0','link'])
    assert 'freq: 5180' in wifi
    (dest/f'wifi-{i}-private.txt').write_text(wifi)
    power=Path('/sys/class/power_supply/mp2650-input/uevent').read_text()
    assert 'POWER_SUPPLY_ONLINE=1\n' in power
    samples.append(dict(sample=i,elapsed=time.monotonic()-start,power_uevent=power))
    if i<7:
        time.sleep(6)
after=cmd(['dmesg'])
(dest/'dmesg-after-private.txt').write_text(after)
assert counts(before)==counts(after)
checks=[]
for args,n in [(['sha256sum','-c','/run/samurai-wifi/nv-source-hashes.txt'],6),(['sha256sum','-c','/var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256'],4),(['sha256sum','-c','/var/lib/samurai/k115-vendor-camera-source/vendor-before.sha256'],1)]:
    text=cmd(args)
    assert text.count(': OK')==n and 'FAILED' not in text
    checks.append(text)
(dest/'sources-check-private.txt').write_text(''.join(checks))
(dest/'boot-id-private.txt').write_text(boot+'\n')
report=dict(stage=135,current_kernel=132,samples=samples,duration_seconds=time.monotonic()-start,same_boot_and_desktop_pids=True,taint=0,bluez_started=True,wifi_5180=True,slpi_offline_and_power_zero=True,nv6_source4_vendor1_preserved=True,fault_counts_before=counts(before),fault_counts_after=counts(after),fault_increments_zero=True,continuous_display_acceptance=False,gpu_load_test_performed=False,charging_control_accepted=False,goal_complete=False)
(dest/'health-private.json').write_text(json.dumps(report,indent=2)+'\n')
subprocess.run(['tar','-C',str(dest),'-czf','/tmp/k135-rollback-health-private.tar.gz','.'],check=True)
print('K135_STABLE132_42_SECOND_PASSIVE_HEALTH_OBSERVATION_PASS',flush=True)
