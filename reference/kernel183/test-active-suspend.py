from pathlib import Path
import array, json, os, re, subprocess, threading, time, wave

os.umask(0o077)
out = Path('/var/lib/samurai/k183-suspend-active')
out.mkdir(mode=0o700)
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert os.uname().version.startswith('#183 ')
assert boot == Path('/var/lib/samurai/k183-runtime/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
assert json.loads(Path('/var/lib/samurai/k183-rtc/validation.json').read_text())['awake_rtc_alarm_irq_delta'] == 1
assert Path('/sys/power/mem_sleep').read_text().strip() == '[s2idle]'
for p in ['pcm0p', 'pcm1c']:
    assert Path('/proc/asound/card0/' + p + '/sub0/status').read_text().strip() == 'closed'
for a in ['1-0039', '1-003a']:
    assert 'powered=0 muted=1' in Path('/sys/bus/i2c/devices/' + a + '/status').read_text()
(out / 'boot-id-private.txt').write_bytes(boot)
alarm = Path('/sys/class/rtc/rtc0/wakealarm')
assert not alarm.read_text().strip(), 'Existing RTC alarm must not be replaced'
assert Path('/sys/class/rtc/rtc0/device/power/wakeup').read_text().strip() == 'enabled'

def phase(value, **fields):
    with (out / 'phase-private.json').open('w') as f:
        json.dump(dict(phase=value, **fields), f, indent=2)
        f.write('\n'); f.flush(); os.fsync(f.fileno())

def stats():
    return {p.name: p.read_text().strip() for p in Path('/sys/power/suspend_stats').iterdir() if p.is_file()}

def irq_count():
    row = next(l for l in Path('/proc/interrupts').read_text().splitlines() if l.endswith('pm8xxx_rtc_alarm'))
    return sum(int(v) for v in row.split()[1:9])

def log():
    return subprocess.check_output(['dmesg'], text=True)


def pulse(args):
    p = subprocess.run(['su', '-s', '/bin/sh', 'cy122', '-c', 'XDG_RUNTIME_DIR=/run/user/10000 ' + args], capture_output=True)
    assert p.returncode == 0, p.stderr.decode(errors='replace')
    return p.stdout.decode()

def audio_state():
    return dict(pcm={p: Path('/proc/asound/card0/' + p + '/sub0/status').read_text().strip() for p in ['pcm0p', 'pcm1c']},
                amps={a: Path('/sys/bus/i2c/devices/' + a + '/status').read_text().strip() for a in ['1-0039', '1-003a']})

saved_mixer = subprocess.check_output(['amixer', '-c', '0', 'contents'])
saved_sinks = pulse('pactl -f json list sinks')
saved_sources = pulse('pactl -f json list sources')
for label, text in [('sinks', saved_sinks), ('sources', saved_sources)]:
    (out / (label + '-before-private.json')).write_text(text)
pcm_data = []
for speaker in ['left', 'right']:
    with wave.open('/var/lib/samurai/k181-dmic0-ucm181-low24/' + speaker + '-stimulus-private.wav', 'rb') as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (2, 2, 48000)
        a = array.array('h'); a.frombytes(w.readframes(w.getnframes())); pcm_data.append(a)
combined = array.array('h')
for i in range(0, len(pcm_data[0]), 2):
    combined.extend([round(pcm_data[0][i] / 4), round(pcm_data[1][i + 1] / 4)])
frames = combined.tobytes() * 3
capture_file = (out / 'active-capture-private.raw').open('wb')
capture_log = (out / 'active-parecord-private.log').open('wb')
play_log = (out / 'active-paplay-private.log').open('wb')
rec = play = writer = None
feed_errors = []
active_before = None
duplex = None

def start_duplex():
    global rec, play, writer, active_before
    rec = subprocess.Popen(['su', '-s', '/bin/sh', 'cy122', '-c',
        'XDG_RUNTIME_DIR=/run/user/10000 timeout -s INT -k 2 20 parecord '
        '--device=alsa_input.platform-sound.HiFi__Mic__source --raw --format=s16le --rate=48000 --channels=1 --volume=65536'],
        stdout=capture_file, stderr=capture_log)
    time.sleep(.5)
    play = subprocess.Popen(['su', '-s', '/bin/sh', 'cy122', '-c',
        'XDG_RUNTIME_DIR=/run/user/10000 paplay --device=alsa_output.platform-sound.HiFi__Speaker__sink '
        '--volume=65536 --raw --format=s16le --rate=48000 --channels=2'], stdin=subprocess.PIPE, stdout=play_log, stderr=play_log)
    def feed():
        try:
            play.stdin.write(frames); play.stdin.close()
        except Exception as e:
            feed_errors.append(str(e))
    writer = threading.Thread(target=feed); writer.start()
    time.sleep(.7)
    active_before = audio_state()
    (out / 'audio-active-before-private.json').write_text(json.dumps(active_before, indent=2) + '\n')
    assert all('RUNNING' in v for v in active_before['pcm'].values())
    assert all('global=01' in v and 'powered=1 muted=0' in v for v in active_before['amps'].values())
    assert play.poll() is None and rec.poll() is None

def finish_duplex():
    global duplex
    play_rc = play.wait(timeout=20)
    capture_rc = rec.wait(timeout=25)
    writer.join(timeout=3)
    assert not writer.is_alive()
    capture_file.flush()
    size = (out / 'active-capture-private.raw').stat().st_size
    deadline = time.monotonic() + 12
    while any(v != 'closed' for v in audio_state()['pcm'].values()) and time.monotonic() < deadline:
        time.sleep(.5)
    final = audio_state()
    after_sinks = pulse('pactl -f json list sinks'); after_sources = pulse('pactl -f json list sources')
    for label, text in [('sinks', after_sinks), ('sources', after_sources)]:
        (out / (label + '-after-private.json')).write_text(text)
    volume = lambda text: {v['name']: (v['volume'], v['mute']) for v in json.loads(text)}
    duplex = dict(playback_returncode=play_rc, capture_returncode=capture_rc, capture_frames=size // 2,
                  planned_capture_timeout=True, stimulus_peak_dbfs=-36, stimulus_duration_seconds=12,
                  both_pcm_running_and_both_amps_on_before_suspend=True, feed_errors=feed_errors,
                  mixer_unchanged=saved_mixer == subprocess.check_output(['amixer', '-c', '0', 'contents']),
                  sink_and_source_volume_mute_unchanged=volume(saved_sinks) == volume(after_sinks) and volume(saved_sources) == volume(after_sources),
                  pcm_closed=all(v == 'closed' for v in final['pcm'].values()),
                  amps_off=all('global=00' in v and 'powered=0 muted=1' in v for v in final['amps'].values()))
    (out / 'duplex-validation.json').write_text(json.dumps(duplex, indent=2) + '\n')

trace = Path('/sys/kernel/tracing/instances/k183-pm')
trace.mkdir()
trace_saved = False
target = None
before = stats(); before_log = log(); before_irq = irq_count()
(out / 'stats-before-private.json').write_text(json.dumps(before, indent=2) + '\n')
(out / 'dmesg-before-private.txt').write_text(before_log)
(out / 'wakeup-before-private.txt').write_text(Path('/sys/kernel/debug/wakeup_sources').read_text())
try:
    (trace / 'buffer_size_kb').write_text('512')
    for name in ['suspend_resume', 'device_pm_callback_start', 'device_pm_callback_end',
                 'wakeup_source_activate', 'wakeup_source_deactivate']:
        (trace / 'events/power' / name / 'enable').write_text('1')
    (trace / 'tracing_on').write_text('1')
    start_duplex()
    phase('preflight-complete-active-duplex')
    time.sleep(.3)
    assert boot == Path('/proc/sys/kernel/random/boot_id').read_bytes()
    assert not alarm.read_text().strip()
    target = int(Path('/sys/class/rtc/rtc0/since_epoch').read_text()) + 90
    alarm.write_text(str(target))
    assert alarm.read_text().strip() == str(target)
    phase('armed-before-suspend', alarm=target, stats=before)
    os.sync()
    monotonic_start = time.monotonic()
    boot_start = time.clock_gettime(time.CLOCK_BOOTTIME)
    result = None
    try:
        Path('/sys/power/state').write_text('mem')
        result = dict(returned=True, errno=0)
    except OSError as e:
        result = dict(returned=True, errno=e.errno, error=str(e))
    monotonic_elapsed = time.monotonic() - monotonic_start
    boot_elapsed = time.clock_gettime(time.CLOCK_BOOTTIME) - boot_start
    phase('returned-from-suspend', result=result, monotonic_elapsed=monotonic_elapsed,
          boottime_elapsed=boot_elapsed)
    (trace / 'tracing_on').write_text('0')
    trace_text = (trace / 'trace').read_text()
    (out / 'pm-trace-private.txt').write_text(trace_text)
    trace_saved = True
    finish_duplex()
    time.sleep(2)
    after = stats(); after_log = log()
    (out / 'stats-after-private.json').write_text(json.dumps(after, indent=2) + '\n')
    (out / 'dmesg-after-private.txt').write_text(after_log)
    (out / 'wakeup-after-private.txt').write_text(Path('/sys/kernel/debug/wakeup_sources').read_text())
    delta = {k: int(after[k]) - int(before[k]) for k in before if re.fullmatch(r'\d+', before[k]) and re.fullmatch(r'\d+', after[k])}
    patterns = {'warnings': 'WARNING:', 'oops': 'Oops:', 'ngd_error_interrupt': 'Error Interrupt received',
                'transfer_timeout': 'failed:-110', 'dma_prepare': 'unable to prepare channel',
                'tx_timeout': 'TX timed out', 'ngd_resume_failed': 'NGD resume failed',
                'asoc_error': 'ASoC error', 'wcd_underflow': 'underflow error', 'wcd_overflow': 'overflow error', 'port_closed': 'Port Closed', 'mfd_bringup_error': 'Failed to bring up WCD934X:'}
    faults = {k: after_log.count(v) - before_log.count(v) for k, v in patterns.items()}
    residency = boot_elapsed - monotonic_elapsed
    report = dict(stage=183, kernel_build=183, requested_state='mem', selected_mem_sleep='s2idle',
                  sysfs_result=result, suspend_stats_delta=delta,
                  last_failed_device=after.get('last_failed_dev'), last_failed_errno=after.get('last_failed_errno'),
                  last_failed_step=after.get('last_failed_step'), alarm_delay_seconds=90,
                  rtc_alarm_irq_delta=irq_count()-before_irq,
                  monotonic_elapsed_seconds=monotonic_elapsed, boottime_elapsed_seconds=boot_elapsed,
                  suspend_residency_seconds=residency, fault_delta=faults,
                  same_boot=boot == Path('/proc/sys/kernel/random/boot_id').read_bytes(),
                  taint=int(Path('/proc/sys/kernel/tainted').read_text()),
                  card_present=Path('/proc/asound/cards').read_text().count('Realme X2 Pro') == 1,
                  active_duplex=duplex, pm_trace_captured=True, trace_isolated_from_existing_display_and_radio_instances=True,
                  no_reboot_or_driver_rebind=True, post_resume_acoustic_validation_pending=True)
    report['suspend_and_rtc_resume_passed'] = bool(result['errno'] == 0 and delta.get('success') == 1 and
                                                delta.get('fail') == 0 and residency >= 45 and
                                                report['rtc_alarm_irq_delta'] == 1 and report['same_boot'] and
                                                report['taint'] == 0 and not any(faults.values()))
    report['active_duplex_survived'] = bool(duplex['playback_returncode'] == 0 and duplex['capture_returncode'] in [0, 124] and duplex['capture_frames'] >= 240000 and not feed_errors and duplex['pcm_closed'] and duplex['amps_off'] and duplex['mixer_unchanged'] and duplex['sink_and_source_volume_mute_unchanged'])
    (out / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    phase('completed', passed=report['suspend_and_rtc_resume_passed'])
    print(json.dumps(report), flush=True)
finally:
    if target is not None and alarm.read_text().strip() == str(target):
        alarm.write_text('0')
    if trace.exists():
        (trace / 'tracing_on').write_text('0')
        if not trace_saved:
            (out / 'pm-trace-private.txt').write_text((trace / 'trace').read_text())
        for name in ['suspend_resume', 'device_pm_callback_start', 'device_pm_callback_end',
                     'wakeup_source_activate', 'wakeup_source_deactivate']:
            (trace / 'events/power' / name / 'enable').write_text('0')
        trace.rmdir()

    for child in [play, rec]:
        if child is not None and child.poll() is None:
            child.terminate(); child.wait(timeout=3)
    if writer is not None:
        writer.join(timeout=3)
    capture_file.close(); capture_log.close(); play_log.close()
