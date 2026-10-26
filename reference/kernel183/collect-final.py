from pathlib import Path
import json
import os
import re
import subprocess
import tarfile

os.umask(0o077)
root = Path('/var/lib/samurai')
out = root / 'k183-final'
out.mkdir(mode=0o700)
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert os.uname().version.startswith('#183 ')
assert boot == (root / 'k183-runtime/boot-id-private.txt').read_bytes()
(out / 'boot-id-private.txt').write_bytes(boot)
def command(args):
    p = subprocess.run(args, capture_output=True, timeout=30)
    assert p.returncode == 0, (args, p.stderr.decode(errors='replace'))
    return p.stdout.decode(errors='replace')
def pulse(args):
    return command(['su', '-s', '/bin/sh', 'cy122', '-c', 'XDG_RUNTIME_DIR=/run/user/10000 ' + args])
def cget(name):
    return re.search(r': values=(.*)', command(['amixer', '-c', '0', 'cget', "name='" + name + "'"]))[1].strip()

fixed = json.loads((root / 'k183-playback-crash-fixed-v2/validation.json').read_text())
assert fixed['kernel_build'] == 183 and fixed['same_boot'] and fixed['taint'] == 0
assert fixed['original_clients_automatically_reconnected'] and not any(fixed['fault_counts'].values())
assert 'Traceback' not in (root / 'k183-fixed-v2-worker-private.log').read_text()
pm = {}
for name in ['idle', 'active']:
    report = json.loads((root / ('k183-suspend-' + name) / 'validation.json').read_text())
    assert report['kernel_build'] == 183 and report['same_boot'] and report['taint'] == 0
    assert report['suspend_and_rtc_resume_passed']
    if name == 'active':
        assert report['active_duplex_survived']
    pm[name] = report
assert json.loads((root / 'k183-pm-sequence/phase-private.json').read_text())['both_passed']
assert 'Traceback' not in (root / 'k183-pm-worker-private.log').read_text()
native = json.loads((root / 'k183-dmic0-ucm183-low24/capture-validation.json').read_text())
desktop = json.loads((root / 'k183-desktop/validation.json').read_text())
assert native['kernel_build'] == desktop['kernel_build'] == 183
assert native['mixer_restored'] and desktop['mixer_restored']
assert boot == (root / 'k183-dmic0-ucm183-low24/boot-id-private.txt').read_bytes()
assert boot == (root / 'k183-desktop/boot-id-private.txt').read_bytes()
assert 'Traceback' not in (root / 'k183-native-postpm-worker-private.log').read_text()
assert 'Traceback' not in (root / 'k183-desktop-worker-private.log').read_text()
historical = json.loads((root / 'k183-playback-crash/validation.json').read_text())
assert historical['kernel_build'] == 181 and historical['fault_counts']['asoc'] == 3
log = command(['dmesg'])
(out / 'dmesg-private.txt').write_text(log)
assert re.match(r'^\[\s*0\.0+\]', log.splitlines()[0]) and '#183 SMP PREEMPT' in log
patterns = {'warning': 'WARNING:', 'oops': 'Oops:', 'asoc': 'ASoC error', 'dma_prepare': 'unable to prepare channel',
            'tx_timeout': 'TX timed out', 'queue_full': 'Message buffer unavailable', 'resume': 'NGD resume failed',
            'irq_read': 'Failed to read IRQ status', 'irq_config': 'Failed to write config', 'irq_mask': 'Failed to sync masks',
            'pdr_listener': 'register listener txn wait failed', 'pdr_missing_state': 'register listener response has no state',
            'bringup': 'Failed to bring up WCD934X:', 'underflow': 'underflow error', 'overflow': 'overflow error',
            'ngd_interrupt': 'Error Interrupt received', 'transfer_timeout': 'failed:-110', 'qmi_wait': 'QMI wait timeout',
            'port_closed': 'Port Closed', 'gpu_fault': 'gpu fault:'}
faults = {key: log.count(value) for key, value in patterns.items()}
assert not any(faults.values()), faults
saved = json.loads((root / 'k183-playback-crash-fixed-v2/mixer-before-private.json').read_text())
assert all(cget(n) == v for n, v in saved.items())
pcm = {p: Path('/proc/asound/card0/' + p + '/sub0/status').read_text().strip() for p in ['pcm0p', 'pcm1c']}
assert all(v == 'closed' for v in pcm.values())
amps = {a: Path('/sys/bus/i2c/devices/' + a + '/status').read_text().strip() for a in ['1-0039', '1-003a']}
counts = {a: {n: int(re.search(n + r'=(\d+)', text)[1]) for n in ['starts', 'stops', 'failed']} for a, text in amps.items()}
assert all(c['starts'] == c['stops'] and c['failed'] == 0 for c in counts.values())
assert all('powered=0 muted=1' in text and 'global=00' in text for text in amps.values())
cards = json.loads(pulse('pactl -f json list cards'))
assert len(cards) == 1 and cards[0]['active_profile'] == 'HiFi (Mic, Speaker)'
assert sum('\tmodule-alsa-card\t' in line for line in pulse('pactl list short modules').splitlines()) == 1
before = json.loads((root / 'k183-playback-crash-fixed-v2/initial-pulse-private.json').read_text())
for key, name in [('sinks', 'alsa_output.platform-sound.HiFi__Speaker__sink'),
                  ('sources', 'alsa_input.platform-sound.HiFi__Mic__source')]:
    old = next(d for d in before[key] if d['name'] == name)
    new = next(d for d in json.loads(pulse('pactl -f json list ' + key)) if d['name'] == name)
    assert old['volume'] == new['volume'] and old['mute'] == new['mute']
maps = {n: (Path('/sys/kernel/debug/regmap') / n / 'name').read_text().strip() for n in ['217:250:0:0', '217:250:1:0']}
assert maps == {'217:250:0:0': 'nodev', '217:250:1:0': 'wcd934x-slim'}
assert Path('/sys/kernel/debug/regmap/217:250:1:0/cache_only').read_text().strip() == 'N'
assert sum(bool(re.match(r'^\s+mclk\s', l)) for l in Path('/sys/kernel/debug/clk/clk_summary').read_text().splitlines()) == 1
supplies = {}
for line in Path('/sys/kernel/debug/regulator/regulator_summary').read_text().splitlines():
    fields = line.split()
    if fields and re.fullmatch(r'217:250:1:0-vdd-(?:io|rx|tx|buck-sido|buck)', fields[0]):
        supplies[fields[0]] = int(fields[1])
assert len(supplies) == 5 and all(v == 1 for v in supplies.values())
command(['sha256sum', '-c', '/run/samurai-wifi/nv-source-hashes.txt'])
command(['sh', '-c', 'cd /usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k132+ && sha256sum -c /var/lib/samurai/k183-preflash/old132-module-tree.sha256'])
hashes = {'/dev/sde11': '77e1a272741aeb09f780a1cff1224098bc78126f1a9154ed5d0c00d91f587a28',
          '/dev/sde32': 'e73754c7d327925acf031aed54e0e6d02069b7a112c32b187ac9bfb468da1358',
          '/dev/sda2': '7e085ef3264e212da7009099113b86ad1f6ec44176840f03f9b85d0e632412f3'}
assert all(command(['sha256sum', path]).split()[0] == digest for path, digest in hashes.items())
report = dict(stage=183, kernel_build=183, same_boot=boot == Path('/proc/sys/kernel/random/boot_id').read_bytes(),
              kernel_version=os.uname().version, uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]),
              taint=int(Path('/proc/sys/kernel/tainted').read_text()), adsp=Path('/sys/class/remoteproc/remoteproc2/state').read_text().strip(),
              full_boot_fault_counts=faults, full_current_boot_log_starts_at_zero=True,
              full_boot_synthetic_crash_report_count=log.count('crash detected in adsp:'),
              matched_control_duplex_crash_passed=True, first_fixed_harness_failure_preserved=True,
              old181_playback_crash_asoc3_failure_preserved=True, current_s2idle_cases=pm,
              post_pm_native_and_desktop_captures_completed_same_boot=True,
              single_card_and_pulse_module=True, active_profile=cards[0]['active_profile'], pcm=pcm,
              amp_counts=counts, amplifiers_off_muted=True, mixer_restored=True, mixer_control_count=len(saved),
              sink_source_volume_mute_unchanged=True, regmap_names=maps, live_main_cache_only=False,
              single_mclk=True, supply_consumer_counts=supplies,
              ngd_pm=Path('/sys/bus/platform/devices/qcom,slim-ngd.1/power/runtime_status').read_text().strip(),
              nv_persist_boot_logdump_and_modules132_verified=True, partition_hashes=hashes,
              physical_headset_real_watchdog_cross_boot_long_stability_and_audio_quality_still_open=True,
              complete_audio_goal_not_achieved=True)
assert report['same_boot'] and report['taint'] == 0 and report['adsp'] == 'running'
(out / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
with tarfile.open('/tmp/k183-all-private.tar.gz', 'w:gz') as t:
    for path in root.glob('k183*'):
        t.add(path, arcname=path.name)
print(json.dumps({k: v for k, v in report.items() if k != 'current_s2idle_cases'}), flush=True)
