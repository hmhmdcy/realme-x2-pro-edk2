from pathlib import Path
import json
import os
import re
import subprocess
import tarfile

os.umask(0o077)
out = Path('/var/lib/samurai/k181-final')
out.mkdir(mode=0o700)
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert os.uname().version.startswith('#181 ')
assert boot == Path('/var/lib/samurai/k181-runtime/boot-id-private.txt').read_bytes()
(out/'boot-id-private.txt').write_bytes(boot)
def cmd(args):
    p = subprocess.run(args, capture_output=True)
    assert p.returncode == 0, (args, p.stderr.decode(errors='replace'))
    return p.stdout.decode(errors='replace')
def pulse(args):
    return cmd(['su','-s','/bin/sh','cy122','-c','XDG_RUNTIME_DIR=/run/user/10000 '+args])

log = cmd(['dmesg'])
(out/'dmesg-private.txt').write_text(log)
first = re.match(r'^\[\s*([0-9.]+)\]', log.splitlines()[0])
assert first and float(first[1]) == 0 and '#181 SMP PREEMPT' in log
patterns = {'warning':'WARNING:', 'oops':'Oops:', 'asoc':'ASoC error',
            'dma_prepare':'unable to prepare channel', 'tx_timeout':'TX timed out',
            'queue_full':'Message buffer unavailable', 'resume_failed':'NGD resume failed',
            'irq_read':'Failed to read IRQ status', 'irq_config':'Failed to write config',
            'irq_mask':'Failed to sync masks', 'pdr_listener':'register listener txn wait failed',
            'pdr_missing_state':'register listener response has no state',
            'bringup':'Failed to bring up WCD934X:', 'ngd_interrupt':'Error Interrupt received',
            'transfer_timeout':'failed:-110', 'underflow':'underflow error', 'overflow':'overflow error',
            'port_closed':'Port Closed', 'qmi_wait':'QMI wait timeout', 'gpu_fault':'gpu fault:'}
faults = {key:log.count(value) for key,value in patterns.items()}
assert not any(faults.values()), faults
restart = json.loads(Path('/var/lib/samurai/k181-adsp-restart/validation.json').read_text())
assert restart['kernel_build'] == 181 and not any(restart['fault_delta'].values())
assert restart['physical_offline_observed'] and restart['capture_running_after_restart']
assert 'Traceback' not in Path('/var/lib/samurai/k181-adsp-worker-private.log').read_text()
native_dir = Path('/var/lib/samurai/k181-dmic0-ucm181-low24')
native = json.loads((native_dir/'capture-validation.json').read_text())
desktop = json.loads(Path('/var/lib/samurai/k181-desktop/validation.json').read_text())
assert native['kernel_build'] == desktop['kernel_build'] == 181
assert native['mixer_restored'] and desktop['mixer_restored']
assert boot == (native_dir/'boot-id-private.txt').read_bytes()
saved = json.loads((native_dir/'mixer-before-private.json').read_text())
assert all(re.search(r': values=(.*)',cmd(['amixer','-c','0','cget',"name='"+name+"'"]))[1].strip()==value for name,value in saved.items())
cmd(['sha256sum','-c','/run/samurai-wifi/nv-source-hashes.txt'])
cmd(['sh','-c','cd /usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k132+ && sha256sum -c /var/lib/samurai/k181-preflash/old132-module-tree.sha256'])
partitions={'/dev/sde11':'77e1a272741aeb09f780a1cff1224098bc78126f1a9154ed5d0c00d91f587a28',
            '/dev/sde32':'56aa1c463d118f9de8d5dbd2cad3dc6b2ab1ff9f36d4027c77d457520b702a55',
            '/dev/sda2':'7e085ef3264e212da7009099113b86ad1f6ec44176840f03f9b85d0e632412f3'}
assert all(cmd(['sha256sum',path]).split()[0]==digest for path,digest in partitions.items())
cards=json.loads(pulse('pactl -f json list cards'))
assert len(cards)==1 and cards[0]['active_profile']=='HiFi (Mic, Speaker)'
assert sum('\tmodule-alsa-card\t' in line for line in pulse('pactl list short modules').splitlines())==1
assert subprocess.run(['pgrep','-x','callaudiod'],stdout=subprocess.DEVNULL).returncode==0
pcm={p:Path('/proc/asound/card0/'+p+'/sub0/status').read_text().strip() for p in ['pcm0p','pcm1c']}
assert all(value=='closed' for value in pcm.values())
amps={a:Path('/sys/bus/i2c/devices/'+a+'/status').read_text().strip() for a in ['1-0039','1-003a']}
counts={a:{n:int(re.search(n+r'=(\d+)',s)[1]) for n in ['starts','stops','failed']} for a,s in amps.items()}
assert all(c['starts']==c['stops'] and c['failed']==0 for c in counts.values())
assert all('powered=0 muted=1' in value for value in amps.values())
names={addr:(Path('/sys/kernel/debug/regmap')/addr/'name').read_text().strip() for addr in ['217:250:0:0','217:250:1:0']}
assert names=={'217:250:0:0':'nodev','217:250:1:0':'wcd934x-slim'}
cache=Path('/sys/kernel/debug/regmap/217:250:1:0/cache_only')
assert cache.is_file() and cache.read_text().strip()=='N'
assert sum(bool(re.match(r'^\s+mclk\s',line)) for line in Path('/sys/kernel/debug/clk/clk_summary').read_text().splitlines())==1
supplies={}
for line in Path('/sys/kernel/debug/regulator/regulator_summary').read_text().splitlines():
    fields=line.split()
    if fields and re.fullmatch(r'217:250:1:0-vdd-(?:io|rx|tx|buck-sido|buck)',fields[0]):
        supplies[fields[0]]=int(fields[1])
assert len(supplies)==5 and all(value==1 for value in supplies.values())
historical=json.loads(Path('/var/lib/samurai/k180-adsp-restart/validation.json').read_text())
assert historical['fault_delta']['irq_config']==72 and historical['fault_delta']['irq_mask']==6
report=dict(stage=181,kernel_build=181,same_boot=boot==Path('/proc/sys/kernel/random/boot_id').read_bytes(),
            uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]),
            taint=int(Path('/proc/sys/kernel/tainted').read_text()),
            adsp=Path('/sys/class/remoteproc/remoteproc2/state').read_text().strip(),
            controlled_adsp_restart_passed=True,initial_boot_and_full_current_ring_fault_counts=faults,
            full_current_boot_log_starts_at_zero=True,single_card_and_pulse_module=True,
            active_profile=cards[0]['active_profile'],pcm=pcm,amp_counts=counts,amplifiers_off_muted=True,
            regmap_names=names,live_main_regmap_cache_only=False,single_mclk=True,
            supply_consumer_counts=supplies,mixer_restored=True,mixer_control_count=len(saved),
            ngd_pm=Path('/sys/bus/platform/devices/qcom,slim-ngd.1/power/runtime_status').read_text().strip(),
            nv_persist_boot_logdump_and_modules132_verified=True,partition_hashes=partitions,
            old180_failed_restart_preserved=True,old180_irq_config72_mask6_not_relabelled_passed=True,
            physical_headset_automatic_crash_long_pm_and_audio_quality_still_open=True,
            complete_audio_goal_not_achieved=True)
assert report['same_boot'] and report['taint']==0 and report['adsp']=='running'
(out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
with tarfile.open('/tmp/k181-all-private.tar.gz','w:gz') as archive:
    for path in Path('/var/lib/samurai').glob('k181*'):
        archive.add(path,arcname=path.name)
print(json.dumps(report),flush=True)
