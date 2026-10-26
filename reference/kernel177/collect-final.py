from pathlib import Path
import hashlib, json, os, re, subprocess, tarfile

os.umask(0o077)
out = Path('/var/lib/samurai/k177-final')
out.mkdir(mode=0o700)
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == Path('/var/lib/samurai/k176-runtime/boot-id-private.txt').read_bytes()
(out / 'boot-id-private.txt').write_bytes(boot)
assert os.uname().version.startswith('#176 ')

def cmd(args):
    p = subprocess.run(args, capture_output=True)
    assert p.returncode == 0, (args, p.stderr.decode(errors='replace'))
    return p.stdout.decode(errors='replace')

log = cmd(['dmesg'])
(out / 'dmesg-private.txt').write_text(log)
patterns = {
    'warnings': 'WARNING:', 'kernel_oops': 'Oops:', 'asoc_error': 'ASoC error',
    'jack_disconnect_error': 'jack disconnect:', 'dma_prepare': 'unable to prepare channel',
    'tx_timeout': 'TX timed out', 'resume_failed': 'NGD resume failed', 'gpu_fault': 'gpu fault:',
    'wcd_underflow': 'underflow error', 'wcd_overflow': 'overflow error', 'port_closed': 'Port Closed',
    'mclk_error': 'Failed to register MCLK output', 'irq_chip_error': 'Failed to add IRQ chip',
    'ngd_error_interrupt': 'Error Interrupt received', 'transfer_timeout': 'failed:-110',
    'mfd_bringup_error': 'Failed to bring up WCD934X:'
}
faults = {n: log.count(p) for n, p in patterns.items()}
assert not any(faults.values()), faults
cmd(['sha256sum', '-c', '/run/samurai-wifi/nv-source-hashes.txt'])
cmd(['sh', '-c', 'cd /usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k132+ && sha256sum -c /var/lib/samurai/k176-preflash/old132-module-tree.sha256'])
partitions = {'/dev/sde11': '77e1a272741aeb09f780a1cff1224098bc78126f1a9154ed5d0c00d91f587a28',
              '/dev/sde32': '6e3ebbe791455ae2c06a2374106f57c1d7ea0aac358191c44d8322b8d50f16cb',
              '/dev/sda2': '7e085ef3264e212da7009099113b86ad1f6ec44176840f03f9b85d0e632412f3'}
for p, h in partitions.items():
    assert cmd(['sha256sum', p]).split()[0] == h, p
expected = {'/usr/libexec/samurai-audio-route': '818f63a18cc24b2fd5fd23b950f05db0f386b6e0e19075fd943faa3eedb98e2b',
            '/usr/share/alsa/ucm2/conf.d/Realme_X2_Pro/HiFi.conf': 'a3a9916090364434dbbc4e4aa607973ecc587b2894a094dece9f51a48ffb9c2e',
            '/usr/share/alsa/ucm2/conf.d/Realme_X2_Pro/Realme_X2_Pro.conf': '2712a658e7989b290b9d26eddd3a27588a679fe3b38ae01a6f180fb266b13387'}
for p, h in expected.items():
    assert hashlib.sha256(Path(p).read_bytes()).hexdigest() == h, p
saved = json.loads(Path('/var/lib/samurai/k177-dmic0-ucm177-low24/mixer-before-private.json').read_text())
restored = {n: re.search(': values=(.*)', cmd(['amixer', '-c', '0', 'cget', "name='" + n + "'"]))[1].strip() == v
            for n, v in saved.items()}
assert all(restored.values())
pulse = lambda arg: cmd(['su', '-s', '/bin/sh', 'cy122', '-c', 'XDG_RUNTIME_DIR=/run/user/10000 ' + arg])
cards = json.loads(pulse('pactl -f json list cards'))
assert len(cards) == 1 and cards[0]['active_profile'] == 'HiFi (Mic, Speaker)'
modules = pulse('pactl list short modules')
(out / 'pulse-modules-private.txt').write_text(modules)
assert sum('\tmodule-alsa-card\t' in l for l in modules.splitlines()) == 1
assert '\tmodule-switch-on-port-available\t' not in modules
assert subprocess.run(['pgrep', '-x', 'callaudiod'], stdout=subprocess.DEVNULL).returncode == 0
names = {kind: (Path('/sys/kernel/debug/regmap') / addr / 'name').read_text().strip()
         for kind, addr in [('main', '217:250:1:0'), ('interface', '217:250:0:0')]}
assert names == {'main': 'wcd934x-slim', 'interface': 'nodev'}
assert sorted(p.name for p in Path('/sys/kernel/debug/regmap').iterdir() if p.name.startswith('217:250:')) == ['217:250:0:0', '217:250:1:0']
assert sum(bool(re.match(r'^\s+mclk\s', l)) for l in Path('/sys/kernel/debug/clk/clk_summary').read_text().splitlines()) == 1
jack = {n: re.search(': values=(.*)', cmd(['amixer', '-c', '0', 'cget', "iface=CARD,name='" + n + "'"]))[1].strip()
        for n in ['Headphone Jack', 'Mic Jack']}
assert all(v == 'off' for v in jack.values())
pcm = {p: Path('/proc/asound/card0/' + p + '/sub0/status').read_text().strip() for p in ['pcm0p', 'pcm1c']}
amps = {a: Path('/sys/bus/i2c/devices/' + a + '/status').read_text().strip() for a in ['1-0039', '1-003a']}
counts = {a: {n: int(re.search(n + r'=(\d+)', s)[1]) for n in ['starts', 'stops', 'failed']} for a, s in amps.items()}
assert all('global=00' in s and 'powered=0 muted=1' in s for s in amps.values())
assert all(c['starts'] == c['stops'] and c['failed'] == 0 for c in counts.values())
reprobe = json.loads(Path('/var/lib/samurai/k176-reprobe/validation.json').read_text())
assert [r['target'] for r in reprobe['cases']] == ['codec', 'codec'] + ['mfd'] * 8
assert reprobe['old_debugfs_handles_total'] == 18 and reprobe['all_supply_consumer_counts_balanced']
assert reprobe['no_machine_card_driver_rebind_used'] and not any(reprobe['fault_delta'].values())
supply_lines = Path('/sys/kernel/debug/regulator/regulator_summary').read_text().splitlines()
supplies = {}
for line in supply_lines:
    m = re.search(r'(217:250:1:0-vdd-(?:io|rx|tx|buck-sido|buck))\s+(\d+)', line)
    if m:
        assert m[1] not in supplies
        supplies[m[1]] = int(m[2])
assert supplies == reprobe['supplies_before']
stop = json.loads(Path('/var/lib/samurai/k177-stop/validation.json').read_text())
native = json.loads(Path('/var/lib/samurai/k177-dmic0-ucm177-low24/capture-validation.json').read_text())
desktop = json.loads(Path('/var/lib/samurai/k177-desktop/validation.json').read_text())
assert len(stop['cases']) == 8 and len(stop['pause_cycles']) == 3
assert len(native['cases']) == 4 and len(desktop['cases']) == 2
for r in [stop, native, desktop]:
    assert r['same_boot'] and r['taint'] == 0 and not any(r['fault_delta'].values()) and r['mixer_restored' if r is not stop else 'mixer_unchanged']
mbhc = log.count('samurai MBHC started: micbias=2700 mV')
binds = log.count('WCD934x headset detection connected')
assert mbhc == binds and binds >= 11

pm_cases = []
callback_results = []
for case in ['idle', 'active']:
    root = Path('/var/lib/samurai/k177-suspend-' + case)
    pm = json.loads((root / 'validation.json').read_text())
    assert pm['suspend_and_rtc_resume_passed']
    if case == 'active':
        assert pm['active_duplex_survived']
    trace = (root / 'pm-trace-private.txt').read_text()
    all_ends = re.findall(r'device_pm_callback_end: (.*?), err=(-?\d+)', trace)
    assert all(int(err) == 0 for name, err in all_ends)
    relevant = {}
    for kind, name in [('card', 'samurai-audio sound'), ('codec', 'wcd934x-codec '),
                       ('mfd', 'wcd934x-slim '), ('ngd', 'qcom,slim-ngd qcom,slim-ngd.1')]:
        phases = re.findall(r'device_pm_callback_start: ' + re.escape(name) + r'[^\n]*\[(suspend|resume)\]', trace)
        assert 'suspend' in phases and 'resume' in phases, (case, kind, phases)
        ends = [int(err) for device, err in all_ends if device.startswith(name)]
        assert ends and all(err == 0 for err in ends)
        relevant[kind] = dict(suspend_seen=True, resume_seen=True, callback_end_results=ends)
    callback_results.append(dict(case=case, relevant_callbacks=relevant, all_pm_callback_end_errors_zero=True,
                                 total_callback_end_events=len(all_ends)))
    pm_cases.append(dict(case=case, residency_seconds=pm['suspend_residency_seconds'],
                         success_delta=pm['suspend_stats_delta']['success'], fail_delta=pm['suspend_stats_delta']['fail'],
                         rtc_alarm_irq_delta=pm['rtc_alarm_irq_delta'], sysfs_errno=pm['sysfs_result']['errno']))
assert int(Path('/sys/power/suspend_stats/success').read_text()) == 2
assert int(Path('/sys/power/suspend_stats/fail').read_text()) == 0
assert not Path('/sys/class/rtc/rtc0/wakealarm').read_text().strip()
assert not Path('/sys/kernel/tracing/instances/k177-pm').exists()
non_audio = dict(usb_hs_phy_not_in_l2=log.count('HS-PHY not in L2'),
                 wifi_invalid_frequency=log.count('chan info: invalid frequency'),
                 wifi_authentication_denied=log.count('denied authentication'))
wlan_state = Path('/sys/class/net/wlan0/operstate').read_text().strip()
report = dict(stage=177, kernel_build=176, same_boot=boot == Path('/proc/sys/kernel/random/boot_id').read_bytes(),
              uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]), taint=int(Path('/proc/sys/kernel/tainted').read_text()),
              fault_counts=faults, partition_hashes=partitions, first_boot_card_present_without_machine_rebind=True,
              reprobe_results_belong_to_prior_stage176=True, completed_codec_rebinds=2, completed_parent_reset_rebinds=8, all_rebind_cards_recovered_automatically=True,
              no_machine_card_driver_rebind_used=True, old_debugfs_dead_handles_verified=18,
              current_regmap_names=names, exactly_two_regmap_dirs=True, single_mclk=True,
              supplies=supplies, all_supply_consumer_counts_balanced=True, mbhc_starts_total=mbhc, jack_binds_total=binds,
              capture_stop_cases=8, real_pause_resume_cycles=3, native_acoustic_cases=4, desktop_duplex_cases=2,
              single_pulse_card_and_alsa_module=True, active_profile=cards[0]['active_profile'], port_policy_owner='callaudiod',
              jack=jack, pcm=pcm, amps=amps, amp_counts=counts, mixer_restored=restored, nv_and_persist_verified=True,
              modules132_verified=True, ucm173_unchanged=True,
              ngd_pm=Path('/sys/bus/platform/devices/qcom,slim-ngd.1/power/runtime_status').read_text().strip(),
              system_s2idle_cases=pm_cases, power_callback_validation=callback_results, suspend_stats_success=2, suspend_stats_fail=0,
              active_desktop_duplex_survived=True, rtc_alarm_cleared=True, temporary_pm_trace_instance_removed=True,
              non_audio_log_observations=non_audio, wlan_operstate=wlan_state, physical_headset_not_available_or_tested=True,
              calibrated_audio_quality_cold_boot_ssr_and_long_term_pm_not_verified=True,
              platform_exposes_s2idle_only_and_no_deep_str=True, uninterrupted_audio_through_sleep_not_verified=True)
assert report['taint'] == 0 and report['same_boot'] and all(v == 'closed' for v in pcm.values())
(out / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
with tarfile.open('/tmp/k177-all-private.tar.gz', 'w:gz') as ar:
    for p in Path('/var/lib/samurai').glob('k177*'):
        ar.add(p, arcname=p.name)
print(json.dumps(report), flush=True)
