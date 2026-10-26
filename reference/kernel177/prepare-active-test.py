from pathlib import Path
import ast

ref = Path(__file__).parent
s = (ref / 'test-system-suspend.py').read_text()
s = s.replace('import json, os, re, subprocess, time', 'import array, json, os, re, subprocess, threading, time, wave')
s = s.replace("Path('/var/lib/samurai/k177-suspend-idle')", "Path('/var/lib/samurai/k177-suspend-active')")
marker = "trace = Path('/sys/kernel/tracing/instances/k177-pm')"
helpers = '''
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
    with wave.open('/var/lib/samurai/k176-dmic0-ucm176-low24/' + speaker + '-stimulus-private.wav', 'rb') as w:
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
    (out / 'audio-active-before-private.json').write_text(json.dumps(active_before, indent=2) + '\\n')
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
    (out / 'duplex-validation.json').write_text(json.dumps(duplex, indent=2) + '\\n')

'''
assert marker in s
s = s.replace(marker, helpers + marker)
s = s.replace("    phase('preflight-complete')\n    time.sleep(3)", "    start_duplex()\n    phase('preflight-complete-active-duplex')\n    time.sleep(.3)")
s = s.replace("    time.sleep(2)\n    after = stats()", "    finish_duplex()\n    time.sleep(2)\n    after = stats()")
s = s.replace("'asoc_error': 'ASoC error',", "'asoc_error': 'ASoC error', 'wcd_underflow': 'underflow error', 'wcd_overflow': 'overflow error', 'port_closed': 'Port Closed',")
s = s.replace("pm_trace_captured=True,", "active_duplex=duplex, pm_trace_captured=True,")
s = s.replace("    (out / 'validation.json').write_text", "    report['active_duplex_survived'] = bool(duplex['playback_returncode'] == 0 and duplex['capture_returncode'] in [0, 124] and duplex['capture_frames'] >= 240000 and not feed_errors and duplex['pcm_closed'] and duplex['amps_off'] and duplex['mixer_unchanged'] and duplex['sink_and_source_volume_mute_unchanged'])\n    (out / 'validation.json').write_text")
s += '''
    for child in [play, rec]:
        if child is not None and child.poll() is None:
            child.terminate(); child.wait(timeout=3)
    if writer is not None:
        writer.join(timeout=3)
    capture_file.close(); capture_log.close(); play_log.close()
'''
ast.parse(s)
(ref / 'test-active-suspend.py').write_text(s)
print('ACTIVE_SUSPEND_TEST_PREPARED')
