from pathlib import Path
import json, os, re, subprocess, tarfile

os.umask(0o077)
out = Path('/var/lib/samurai/k178-final'); out.mkdir(mode=0o700)
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == Path('/var/lib/samurai/k178-runtime/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#176 ')
(out / 'boot-id-private.txt').write_bytes(boot)

def cmd(args):
    p = subprocess.run(args, capture_output=True)
    assert p.returncode == 0, (args, p.stderr.decode(errors='replace'))
    return p.stdout.decode(errors='replace')

def pulse(args):
    return cmd(['su', '-s', '/bin/sh', 'cy122', '-c', 'XDG_RUNTIME_DIR=/run/user/10000 ' + args])

log = cmd(['dmesg']); (out / 'dmesg-current-private.txt').write_text(log)
baseline = Path('/var/lib/samurai/k178-dmic0-ucm178-low24/dmesg-before-private.txt').read_text().splitlines()
cutoff_line = baseline[-1]
assert cutoff_line in log.splitlines(), 'Acoustic baseline fell out of the kernel ring: evidence incomplete'
cutoff = float(re.match(r'^\[\s*([0-9.]+)\]', cutoff_line)[1])
new = '\n'.join(l for l in log.splitlines() if (m := re.match(r'^\[\s*([0-9.]+)\]', l)) and float(m[1]) > cutoff)
patterns = {'warnings': 'WARNING:', 'oops': 'Oops:', 'asoc_error': 'ASoC error', 'dma_prepare': 'unable to prepare channel',
            'tx_timeout': 'TX timed out', 'ngd_error_interrupt': 'Error Interrupt received', 'transfer_timeout': 'failed:-110',
            'bringup_error': 'Failed to bring up WCD934X:', 'resume_failed': 'NGD resume failed',
            'irq_read_error': 'Failed to read IRQ status:', 'irq_config_error': 'Failed to write config',
            'irq_mask_sync_error': 'Failed to sync masks', 'pdr_listener_error': 'register listener txn wait failed',
            'underflow': 'underflow error', 'overflow': 'overflow error', 'port_closed': 'Port Closed'}
latest_faults = {k: new.count(v) for k, v in patterns.items()}
assert not any(latest_faults.values()), latest_faults
failed = json.loads(Path('/var/lib/samurai/k178-adsp-restart/failure-audit.json').read_text())
assert failed['original_test_did_not_pass'] and failed['counts']['asoc_error'] == 6
cmd(['sha256sum', '-c', '/run/samurai-wifi/nv-source-hashes.txt'])
cmd(['sh', '-c', 'cd /usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k132+ && sha256sum -c /var/lib/samurai/k176-preflash/old132-module-tree.sha256'])
partitions = {'/dev/sde11': '77e1a272741aeb09f780a1cff1224098bc78126f1a9154ed5d0c00d91f587a28',
              '/dev/sde32': '6e3ebbe791455ae2c06a2374106f57c1d7ea0aac358191c44d8322b8d50f16cb',
              '/dev/sda2': '7e085ef3264e212da7009099113b86ad1f6ec44176840f03f9b85d0e632412f3'}
for p, h in partitions.items(): assert cmd(['sha256sum', p]).split()[0] == h
saved = json.loads(Path('/var/lib/samurai/k178-dmic0-ucm178-low24/mixer-before-private.json').read_text())
assert all(re.search(': values=(.*)', cmd(['amixer', '-c', '0', 'cget', "name='" + n + "'"]))[1].strip() == v for n, v in saved.items())
cards = json.loads(pulse('pactl -f json list cards')); assert len(cards) == 1 and cards[0]['active_profile'] == 'HiFi (Mic, Speaker)'
module_text = pulse('pactl list short modules')
assert sum('\tmodule-alsa-card\t' in l for l in module_text.splitlines()) == 1
assert subprocess.run(['pgrep', '-x', 'callaudiod'], stdout=subprocess.DEVNULL).returncode == 0
pcm = {p: Path('/proc/asound/card0/' + p + '/sub0/status').read_text().strip() for p in ['pcm0p', 'pcm1c']}
amps = {a: Path('/sys/bus/i2c/devices/' + a + '/status').read_text().strip() for a in ['1-0039', '1-003a']}
counts = {a: {n: int(re.search(n + r'=(\d+)', s)[1]) for n in ['starts', 'stops', 'failed']} for a, s in amps.items()}
assert all(c['starts'] == c['stops'] and c['failed'] == 0 for c in counts.values())
assert all('powered=0 muted=1' in s for s in amps.values()) and all(v == 'closed' for v in pcm.values())
names = {addr: (Path('/sys/kernel/debug/regmap') / addr / 'name').read_text().strip() for addr in ['217:250:0:0', '217:250:1:0']}
assert names == {'217:250:0:0': 'nodev', '217:250:1:0': 'wcd934x-slim'}
assert sum(bool(re.match(r'^\s+mclk\s', l)) for l in Path('/sys/kernel/debug/clk/clk_summary').read_text().splitlines()) == 1
supplies = {}
for line in Path('/sys/kernel/debug/regulator/regulator_summary').read_text().splitlines():
    f = line.split()
    if f and re.fullmatch(r'217:250:1:0-vdd-(?:io|rx|tx|buck-sido|buck)', f[0]): supplies[f[0]] = int(f[1])
assert len(supplies) == 5 and all(v == 1 for v in supplies.values())
report = dict(stage=178, kernel_build=176, same_boot=boot == Path('/proc/sys/kernel/random/boot_id').read_bytes(),
              uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]), taint=int(Path('/proc/sys/kernel/tainted').read_text()),
              adsp=Path('/sys/class/remoteproc/remoteproc2/state').read_text().strip(), known_failed_restart_counts=failed['counts'],
              controlled_adsp_restart_did_not_pass=True, postfailure_acoustic_window_fault_counts=latest_faults,
              kernel_ring_rotated_but_original_failure_logs_preserved=True,
              single_card_and_pulse_module=True, active_profile=cards[0]['active_profile'], pcm=pcm, amps=amps, amp_counts=counts,
              regmap_names=names, single_mclk=True, supply_consumer_counts=supplies, mixer_restored=True,
              ngd_pm=Path('/sys/bus/platform/devices/qcom,slim-ngd.1/power/runtime_status').read_text().strip(),
              nv_persist_boot_logdump_and_modules132_verified=True, partition_hashes=partitions,
              no_new_kernel_build_flash_or_machine_driver_rebind=True, complete_audio_goal_not_achieved=True)
assert report['taint'] == 0 and report['same_boot'] and report['adsp'] == 'running'
(out / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
with tarfile.open('/tmp/k178-all-private.tar.gz', 'w:gz') as ar:
    for p in Path('/var/lib/samurai').glob('k178*'): ar.add(p, arcname=p.name)
print(json.dumps(report), flush=True)
