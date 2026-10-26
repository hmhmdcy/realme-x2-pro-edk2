from pathlib import Path
import errno, hashlib, json, os, re, subprocess, time

os.umask(0o077)
out = Path('/var/lib/samurai/k178-adsp-restart')
out.mkdir(mode=0o700)
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert os.uname().version.startswith('#176 ')
assert boot == Path('/var/lib/samurai/k177-final/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
(out / 'boot-id-private.txt').write_bytes(boot)
adsp = [p for p in Path('/sys/class/remoteproc').iterdir() if (p / 'name').read_text().strip() == 'adsp']
assert len(adsp) == 1
state = adsp[0] / 'state'
assert state.read_text().strip() == 'running'
assert (adsp[0] / 'recovery').read_text().strip() == 'enabled'

def cmd(args):
    p = subprocess.run(args, capture_output=True)
    assert p.returncode == 0, (args, p.stderr.decode(errors='replace'))
    return p.stdout.decode(errors='replace')

def pulse(args):
    return cmd(['su', '-s', '/bin/sh', 'cy122', '-c', 'XDG_RUNTIME_DIR=/run/user/10000 ' + args])

def phase(name, **extra):
    with (out / 'phase-private.json').open('w') as f:
        json.dump(dict(phase=name, **extra), f, indent=2)
        f.write('\n'); f.flush(); os.fsync(f.fileno())

def supplies():
    rows = {}
    for line in Path('/sys/kernel/debug/regulator/regulator_summary').read_text().splitlines():
        fields = line.split()
        if fields and re.fullmatch(r'217:250:1:0-vdd-(?:io|rx|tx|buck-sido|buck)', fields[0]):
            assert fields[0] not in rows
            rows[fields[0]] = int(fields[1])
    return rows

def maps():
    return sorted(p.name for p in Path('/sys/kernel/debug/regmap').iterdir() if p.name.startswith('217:250:'))

def mclks():
    return sum(bool(re.match(r'^\s+mclk\s', line)) for line in Path('/sys/kernel/debug/clk/clk_summary').read_text().splitlines())

def snapshot(label):
    row = dict(adsp=state.read_text().strip(), cards=Path('/proc/asound/cards').read_text(),
               remoteproc={p.name: dict(name=(p / 'name').read_text().strip(), state=(p / 'state').read_text().strip())
                           for p in Path('/sys/class/remoteproc').iterdir()},
               supplies=supplies(), regmaps=maps(), mclk_count=mclks(),
               amps={a: Path('/sys/bus/i2c/devices/' + a + '/status').read_text().strip() for a in ['1-0039', '1-003a']})
    (out / (label + '-private.json')).write_text(json.dumps(row, indent=2) + '\n')
    return row

def wait_for(predicate, count=80):
    for _ in range(count):
        if predicate():
            return
        time.sleep(.25)
    raise RuntimeError('Timed out waiting for state: ' + state.read_text().strip())

before_log = cmd(['dmesg']); (out / 'dmesg-before-private.txt').write_text(before_log)
cmd(['sha256sum', '-c', '/run/samurai-wifi/nv-source-hashes.txt'])
assert cmd(['sha256sum', '/dev/sde32']).split()[0] == '6e3ebbe791455ae2c06a2374106f57c1d7ea0aac358191c44d8322b8d50f16cb'
before = snapshot('before')
assert maps() == ['217:250:0:0', '217:250:1:0'] and mclks() == 1
assert len(before['supplies']) == 5 and all(v == 1 for v in before['supplies'].values())
fds = {}; stop_ack = False; start_attempted = False; stopped_physically = False
try:
    pulse('pactl suspend-sink alsa_output.platform-sound.HiFi__Speaker__sink 1')
    pulse('pactl suspend-source alsa_input.platform-sound.HiFi__Mic__source 1')
    for p in ['pcm0p', 'pcm1c']:
        assert Path('/proc/asound/card0/' + p + '/sub0/status').read_text().strip() == 'closed'
    assert all('powered=0 muted=1' in v for v in before['amps'].values())
    for addr in maps():
        fds[addr] = os.open(str(Path('/sys/kernel/debug/regmap') / addr / 'name'), os.O_RDONLY)
    assert boot == Path('/proc/sys/kernel/random/boot_id').read_bytes()
    assert state.read_text().strip() == 'running'
    phase('before-single-stop', target=str(adsp[0].resolve()))
    os.sync()
    state.write_text('stop'); stop_ack = True
    phase('stop-returned', state=state.read_text().strip())
    if state.read_text().strip() == 'running':
        # A successful shutdown can consume one power reference without stopping.
        start_attempted = True
        phase('balancing-start-for-reference-only-stop')
        state.write_text('start')
        phase('reference-balanced-without-physical-stop')
        raise RuntimeError('ADSP did not stop: additional power reference; no repeated stop sent')
    assert state.read_text().strip() == 'offline'
    stopped_physically = True
    wait_for(lambda: 'Realme X2 Pro' not in Path('/proc/asound/cards').read_text() and not maps() and mclks() == 0)
    wait_for(lambda: not json.loads(pulse('pactl -f json list cards')))
    off = snapshot('offline')
    assert not off['supplies'] or all(v == 0 for v in off['supplies'].values())
    assert all('powered=0 muted=1' in v for v in off['amps'].values())
    dead = {}
    for name, fd in fds.items():
        try:
            value = os.pread(fd, 64, 0)
            raise RuntimeError('Old regmap name still readable after removal: ' + repr(value))
        except OSError as e:
            assert e.errno in [errno.EIO, errno.ENODEV, errno.ENOENT]
            dead[name] = e.errno
    phase('offline-resources-removed', dead_handles=dead)
    assert boot == Path('/proc/sys/kernel/random/boot_id').read_bytes()
    assert state.read_text().strip() == 'offline'
    start_attempted = True
    phase('before-single-start')
    state.write_text('start')
    phase('start-returned', state=state.read_text().strip())
    wait_for(lambda: state.read_text().strip() == 'running' and 'Realme X2 Pro' in Path('/proc/asound/cards').read_text(), 240)
    def ready_pulse():
        cards = json.loads(pulse('pactl -f json list cards'))
        return len(cards) == 1 and cards[0]['active_profile'] == 'HiFi (Mic, Speaker)'
    wait_for(ready_pulse, 160)
    assert supplies() == before['supplies'] and maps() == before['regmaps'] and mclks() == 1
    names = {addr: (Path('/sys/kernel/debug/regmap') / addr / 'name').read_text().strip() for addr in maps()}
    assert names == {'217:250:0:0': 'nodev', '217:250:1:0': 'wcd934x-slim'}
    pulse('pactl suspend-source alsa_input.platform-sound.HiFi__Mic__source 1')
    with (out / 'capture-after-restart-private.log').open('wb') as log:
        p = subprocess.Popen(['arecord', '-q', '-D', 'hw:0,1', '-r', '48000', '-c', '1', '-f', 'S16_LE', '-d', '1',
                              str(out / 'capture-after-restart-private.wav')], stdout=log, stderr=log)
        try:
            time.sleep(.25)
            assert 'RUNNING' in Path('/proc/asound/card0/pcm1c/sub0/status').read_text()
            assert p.wait(timeout=4) == 0
        finally:
            if p.poll() is None:
                p.terminate(); p.wait(timeout=3)
    pulse('pactl suspend-sink alsa_output.platform-sound.HiFi__Speaker__sink 0')
    pulse('pactl suspend-source alsa_input.platform-sound.HiFi__Mic__source 0')
    wait_for(lambda: all(Path('/proc/asound/card0/' + p + '/sub0/status').read_text().strip() == 'closed' for p in ['pcm0p', 'pcm1c']))
    after = snapshot('after')
    after_log = cmd(['dmesg']); (out / 'dmesg-after-private.txt').write_text(after_log)
    patterns = {'warnings': 'WARNING:', 'oops': 'Oops:', 'asoc_error': 'ASoC error', 'jack_disconnect': 'jack disconnect:',
                'dma_prepare': 'unable to prepare channel', 'tx_timeout': 'TX timed out', 'ngd_error_interrupt': 'Error Interrupt received',
                'transfer_timeout': 'failed:-110', 'bringup_error': 'Failed to bring up WCD934X:', 'resume_failed': 'NGD resume failed',
                'underflow': 'underflow error', 'overflow': 'overflow error', 'port_closed': 'Port Closed', 'qmi_wait_timeout': 'QMI wait timeout'}
    faults = {k: after_log.count(v)-before_log.count(v) for k, v in patterns.items()}
    report = dict(stage=178, kernel_build=176, controlled_adsp_stop_start_once=True, physical_offline_observed=stopped_physically,
                  slimbus_regmaps_mclk_and_card_removed=True, five_supplies_released_and_restored=True, old_debugfs_errno=dead,
                  card_and_pulse_profile_recovered_without_driver_rebind=True, active_profile='HiFi (Mic, Speaker)',
                  capture_running_after_restart=True, current_regmap_names=names,
                  same_boot=boot == Path('/proc/sys/kernel/random/boot_id').read_bytes(), taint=int(Path('/proc/sys/kernel/tainted').read_text()),
                  fault_delta=faults, remoteproc_before=before['remoteproc'], remoteproc_after=after['remoteproc'],
                  amp_status=after['amps'], no_kernel_flash_or_machine_rebind=True, acoustic_and_crash_recovery_not_yet_verified=True)
    (out / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    phase('completed', fault_delta=faults)
    print(json.dumps(report), flush=True)
    assert report['same_boot'] and report['taint'] == 0 and not any(faults.values()), faults
finally:
    for fd in fds.values():
        os.close(fd)
    if stop_ack and not start_attempted and state.read_text().strip() == 'offline' and boot == Path('/proc/sys/kernel/random/boot_id').read_bytes():
        start_attempted = True
        phase('restoration-start-after-test-failure')
        state.write_text('start')
        phase('restoration-start-returned', state=state.read_text().strip())
