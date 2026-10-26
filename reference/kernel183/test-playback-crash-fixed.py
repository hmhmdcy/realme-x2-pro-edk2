"""One synthetic ADSP crash report during the original desktop duplex stream."""
from pathlib import Path
import errno
import hashlib
import json
import os
import queue
import re
import subprocess
import threading
import time
import wave

os.umask(0o077)
out = Path('/var/lib/samurai/k183-playback-crash-fixed')
out.mkdir(mode=0o700)
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert os.uname().version.startswith('#183 ')
assert boot == Path('/var/lib/samurai/k183-runtime/boot-id-private.txt').read_bytes()
(out / 'boot-id-private.txt').write_bytes(boot)
state = Path('/sys/class/remoteproc/remoteproc2/state')
debug = Path('/sys/kernel/debug/remoteproc/remoteproc2')
assert state.read_text().strip() == 'running' and (debug / 'name').read_text().strip() == 'adsp'
assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
assert (debug / 'recovery').read_text().strip() == 'enabled'
assert (debug / 'coredump').read_text().strip() == 'disabled'
sink_name = 'alsa_output.platform-sound.HiFi__Speaker__sink'
mic_name = 'alsa_input.platform-sound.HiFi__Mic__source'
def command(args):
    p = subprocess.run(args, capture_output=True, timeout=15)
    assert p.returncode == 0, (args, p.stderr.decode(errors='replace'))
    return p.stdout.decode(errors='replace')
def pulse(args):
    return command(['su', '-s', '/bin/sh', 'cy122', '-c', 'XDG_RUNTIME_DIR=/run/user/10000 ' + args])
def read(path):
    try:
        return Path(path).read_text().strip()
    except OSError as e:
        if e.errno in [errno.ENOENT, errno.ENODEV, errno.EIO]:
            return 'absent'
        raise
def phase(name, **data):
    with (out / 'phase-private.json').open('w') as f:
        json.dump(dict(phase=name, monotonic=time.monotonic(), **data), f, indent=2)
        f.write('\n'); f.flush(); os.fsync(f.fileno())
def wait_for(fn, seconds):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        if fn():
            return
        time.sleep(.1)
    raise RuntimeError('Condition timed out; do not inject again')
def maps():
    return sorted(p.name for p in Path('/sys/kernel/debug/regmap').iterdir()
                  if p.name.startswith('217:250:'))
def supplies():
    result = {}
    for line in Path('/sys/kernel/debug/regulator/regulator_summary').read_text().splitlines():
        fields = line.split()
        if fields and re.fullmatch(r'217:250:1:0-vdd-(?:io|rx|tx|buck-sido|buck)', fields[0]):
            result[fields[0]] = int(fields[1])
    return result
def amps():
    return {a: read('/sys/bus/i2c/devices/' + a + '/status') for a in ['1-0039', '1-003a']}
def pcm(p):
    return read('/proc/asound/card0/' + p + '/sub0/status')
def cget(name):
    return re.search(r': values=(.*)', command(['amixer', '-c', '0', 'cget', "name='" + name + "'"]))[1].strip()
def save_pulse(label):
    result = {}
    for key in ['cards', 'sinks', 'sources', 'sink-inputs', 'source-outputs']:
        result[key] = json.loads(pulse('pactl -f json list ' + key))
    (out / (label + '-pulse-private.json')).write_text(json.dumps(result, indent=2) + '\n')
    return result

assert all(pcm(p) == 'closed' for p in ['pcm0p', 'pcm1c'])
assert all('powered=0 muted=1' in s for s in amps().values())
assert maps() == ['217:250:0:0', '217:250:1:0']
initial_supplies = supplies()
assert len(initial_supplies) == 5 and all(v == 1 for v in initial_supplies.values())
saved = json.loads(Path('/var/lib/samurai/k181-dmic0-ucm181-low24/mixer-before-private.json').read_text())
saved = {name: cget(name) for name in saved}
(out / 'mixer-before-private.json').write_text(json.dumps(saved, indent=2) + '\n')
initial_pulse = save_pulse('initial')
assert len(initial_pulse['cards']) == 1 and initial_pulse['cards'][0]['active_profile'] == 'HiFi (Mic, Speaker)'
assert not initial_pulse['sink-inputs'] and not initial_pulse['source-outputs']
before_log = command(['dmesg'])
(out / 'dmesg-before-private.txt').write_text(before_log)
start_uptime = float(Path('/proc/uptime').read_text().split()[0])
stimuli = {}
stimulus_hashes = {}
for speaker in ['left', 'right']:
    path = Path('/var/lib/samurai/k181-dmic0-ucm181-low24') / (speaker + '-stimulus-private.wav')
    stimulus_hashes[speaker] = hashlib.sha256(path.read_bytes()).hexdigest()
    with wave.open(str(path)) as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (2, 2, 48000)
        stimuli[speaker] = w.readframes(w.getnframes())

samples = []; monitor_errors = []; writer_errors = []; jobs_done = []
stop = threading.Event(); feed_stop = threading.Event(); jobs = queue.Queue()
raw = out / 'original-capture-private.raw'
def monitor():
    while not stop.is_set():
        try:
            samples.append(dict(t=time.monotonic(), adsp=read(state), cards=read('/proc/asound/cards'),
                                maps=maps(), playback=pcm('pcm0p'), capture=pcm('pcm1c'), amps=amps()))
        except Exception as e:
            monitor_errors.append(repr(e))
        stop.wait(.025)
def writer():
    current = None; offset = 0; frame_count = 0
    try:
        while not feed_stop.is_set():
            if current is None:
                try:
                    current = jobs.get_nowait(); offset = 0
                    current['started_at'] = time.monotonic()
                    current['raw_position_seconds'] = raw.stat().st_size / (2 * 48000)
                    current['input_frame_position'] = frame_count
                    current['started'].set()
                except queue.Empty:
                    pass
            chunk = bytes(3840) if current is None else current['frames'][offset:offset + 3840]
            tick = time.monotonic()
            play.stdin.write(chunk); play.stdin.flush()
            frame_count += len(chunk) // 4
            if current is not None:
                offset += len(chunk)
                if offset == len(current['frames']):
                    current['done_at'] = time.monotonic()
                    jobs_done.append({k: v for k, v in current.items() if k not in ['frames', 'started', 'done']})
                    current['done'].set(); current = None
            feed_stop.wait(max(0, .02 - (time.monotonic() - tick)))
    except Exception as e:
        writer_errors.append(repr(e))
    finally:
        try:
            play.stdin.close()
        except OSError:
            pass
def enqueue(name, speaker, enabled=True):
    job = dict(case=name, speaker=speaker, target_speaker_enabled=enabled, frames=stimuli[speaker], started=threading.Event(), done=threading.Event())
    jobs.put(job)
    assert job['started'].wait(12), 'Original writer stopped before job began'
    return job

rec = play = watcher = feeder = None
fds = {}; injected_at = None; recovered_at = None; muted_targets = set()
try:
    for name in maps():
        fds[name] = os.open(str(Path('/sys/kernel/debug/regmap') / name / 'name'), os.O_RDONLY)
    with raw.open('wb') as destination, (out / 'parecord-private.log').open('wb') as rec_log, \
            (out / 'paplay-private.log').open('wb') as play_log:
        rec = subprocess.Popen(['su', '-s', '/bin/sh', 'cy122', '-c',
            'XDG_RUNTIME_DIR=/run/user/10000 parecord --device=' + mic_name +
            ' --raw --format=s16le --rate=48000 --channels=1 --volume=65536'], stdout=destination, stderr=rec_log)
        wait_for(lambda: 'RUNNING' in pcm('pcm1c'), 5)
        play = subprocess.Popen(['su', '-s', '/bin/sh', 'cy122', '-c',
            'XDG_RUNTIME_DIR=/run/user/10000 paplay --device=' + sink_name +
            ' --raw --format=s16le --rate=48000 --channels=2 --latency-msec=50 --volume=65536'],
            stdin=subprocess.PIPE, stdout=play_log, stderr=play_log)
        feeder = threading.Thread(target=writer); feeder.start()
        wait_for(lambda: 'RUNNING' in pcm('pcm0p') and 'RUNNING' in pcm('pcm1c'), 5)
        assert all('powered=1 muted=0' in s and 'failed=0' in s for s in amps().values())
        live_pulse = save_pulse('before-crash')
        watcher = threading.Thread(target=monitor); watcher.start()
        phase('preflight-complete-before-precrash-code')
        os.sync()
        pre = enqueue('right-before-and-during-crash', 'right')
        time.sleep(.65)
        assert boot == Path('/proc/sys/kernel/random/boot_id').read_bytes()
        assert read(state) == 'running' and rec.poll() is None and play.poll() is None
        assert all('RUNNING' in pcm(p) for p in ['pcm0p', 'pcm1c'])
        assert all('powered=1 muted=0' in s for s in amps().values())
        injected_at = time.monotonic()
        phase('before-single-crash-report', capture_and_playback_running=True, pre_code_started_at=pre['started_at'])
        (debug / 'crash').write_text('0\n')
        phase('single-crash-report-submitted', injected_at=injected_at)
        wait_for(lambda: any(not s['maps'] and 'Realme X2 Pro' not in s['cards'] for s in samples), 30)
        def ready():
            if read(state) != 'running' or 'Realme X2 Pro' not in read('/proc/asound/cards'):
                return False
            cards = json.loads(pulse('pactl -f json list cards'))
            return len(cards) == 1 and cards[0]['active_profile'] == 'HiFi (Mic, Speaker)'
        wait_for(ready, 60)
        wait_for(lambda: all('RUNNING' in pcm(p) for p in ['pcm0p', 'pcm1c']), 15)
        recovered_at = time.monotonic()
        assert rec.poll() is None and play.poll() is None and not writer_errors
        restored_pulse = save_pulse('after-recovery')
        assert len(live_pulse['sink-inputs']) == len(restored_pulse['sink-inputs']) == 1
        assert len(live_pulse['source-outputs']) == len(restored_pulse['source-outputs']) == 1
        for key, device_key, name, route in [('sink-inputs', 'sinks', sink_name, 'sink'),
                                              ('source-outputs', 'sources', mic_name, 'source')]:
            assert live_pulse[key][0]['index'] == restored_pulse[key][0]['index']
            device = next(d for d in restored_pulse[device_key] if d['name'] == name)
            assert restored_pulse[key][0][route] == device['index']
        assert supplies() == initial_supplies
        old_errno = {}
        for name, fd in fds.items():
            try:
                os.pread(fd, 64, 0)
                raise RuntimeError('Old regmap FD remained valid')
            except OSError as e:
                assert e.errno in [errno.EIO, errno.ENODEV, errno.ENOENT]
                old_errno[name] = e.errno
        phase('original-clients-automatically-reconnected', original_clients_alive=True)
        assert pre['done'].wait(8)
        for speaker in ['left', 'right']:
            job = enqueue(speaker + '-after-recovery', speaker)
            assert job['done'].wait(8)
            name = speaker.capitalize() + ' Speaker Switch'
            command(['amixer', '-c', '0', 'cset', "name='" + name + "'", 'off'])
            muted_targets.add(name)
            address = '1-0039' if speaker == 'left' else '1-003a'
            assert 'powered=0 muted=1' in amps()[address]
            job = enqueue(speaker + '-off-control-after-recovery', speaker, False)
            assert job['done'].wait(8)
            command(['amixer', '-c', '0', 'cset', "name='" + name + "'", saved[name]])
            muted_targets.remove(name)
        time.sleep(.8)
        feed_stop.set(); feeder.join(timeout=3); assert not feeder.is_alive()
        assert play.wait(timeout=8) == 0
        rec.send_signal(2)
        try:
            rec.wait(timeout=4)
        except subprocess.TimeoutExpired:
            rec.terminate(); rec.wait(timeout=3)
    frames = raw.read_bytes()
    assert len(frames) % 2 == 0
    with wave.open(str(out / 'original-capture-private.wav'), 'wb') as w:
        w.setparams((1, 2, 48000, 0, 'NONE', 'not compressed')); w.writeframes(frames)
finally:
    feed_stop.set()
    for proc in [play, rec]:
        if proc and proc.poll() is None:
            proc.terminate(); proc.wait(timeout=4)
    if feeder:
        feeder.join(timeout=3)
    for name in muted_targets:
        if Path('/proc/asound/card0').exists():
            command(['amixer', '-c', '0', 'cset', "name='" + name + "'", saved[name]])
    stop.set()
    if watcher:
        watcher.join(timeout=3)
    for fd in fds.values():
        os.close(fd)
    (out / 'timeline-private.json').write_text(json.dumps(samples, indent=2) + '\n')
    (out / 'jobs-private.json').write_text(json.dumps(jobs_done, indent=2) + '\n')
    (out / 'thread-errors-private.json').write_text(json.dumps(dict(monitor=monitor_errors, writer=writer_errors), indent=2) + '\n')
    (out / 'dmesg-after-private.txt').write_text(command(['dmesg']))

wait_for(lambda: all(pcm(p) == 'closed' for p in ['pcm0p', 'pcm1c']), 12)
final_pulse = save_pulse('final')
for key, name in [('sinks', sink_name), ('sources', mic_name)]:
    old = next(d for d in initial_pulse[key] if d['name'] == name)
    new = next(d for d in final_pulse[key] if d['name'] == name)
    assert old['volume'] == new['volume'] and old['mute'] == new['mute']
assert all(cget(name) == value for name, value in saved.items())
assert all('powered=0 muted=1' in s for s in amps().values())
log = command(['dmesg'])
window = '\n'.join(l for l in log.splitlines() if (m := re.match(r'^\[\s*(\d+\.\d+)\]', l)) and float(m[1]) >= start_uptime)
patterns = {'warning': 'WARNING:', 'oops': 'Oops:', 'asoc': 'ASoC error', 'dma_prepare': 'unable to prepare channel',
            'tx_timeout': 'TX timed out', 'queue_full': 'Message buffer unavailable', 'resume': 'NGD resume failed',
            'irq_read': 'Failed to read IRQ status', 'irq_config': 'Failed to write config', 'irq_mask': 'Failed to sync masks',
            'pdr_listener': 'register listener txn wait failed', 'pdr_missing_state': 'register listener response has no state',
            'bringup': 'Failed to bring up WCD934X:', 'underflow': 'underflow error', 'overflow': 'overflow error',
            'ngd_interrupt': 'Error Interrupt received', 'transfer_timeout': 'failed:-110', 'qmi_wait': 'QMI wait timeout'}
faults = {key: window.count(value) for key, value in patterns.items()}
expected = {key: window.count(value) for key, value in {'report': 'crash detected in adsp:',
            'handler': 'handling crash #', 'recovery': 'recovering adsp'}.items()}
report = dict(stage=183, kernel_build=183, same_boot=boot == Path('/proc/sys/kernel/random/boot_id').read_bytes(),
              taint=int(Path('/proc/sys/kernel/tainted').read_text()), synthetic_crash_report_count=1,
              capture_and_playback_running_at_injection=True, original_clients_automatically_reconnected=True,
              original_paplay_returncode=play.returncode, original_parecord_returncode=rec.returncode,
              old_debugfs_errno=old_errno, injection_to_duplex_running_seconds=recovered_at - injected_at,
              timeline_nominal_poll_interval_seconds=.025, jobs=jobs_done, recorded_frames=len(frames) // 2,
              fault_counts=faults, expected_recovery_log_counts=expected, stimulus_hashes=stimulus_hashes,
              source_sink_volume_and_mute_unchanged=True, mixer_restored=True, amplifiers_off_muted=True,
              pcms_closed=True, monitor_errors=monitor_errors, writer_errors=writer_errors,
              no_manual_restart_rebind_or_replacement_client=True, actual_dsp_firmware_watchdog_not_injected=True,
              acoustic_analysis_pending=True)
(out / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
phase('completed', faults=faults)
print(json.dumps({k: v for k, v in report.items() if k != 'jobs'}), flush=True)
assert report['same_boot'] and report['taint'] == 0 and not monitor_errors and not writer_errors
assert all(v == 1 for v in expected.values()) and not any(faults.values())
