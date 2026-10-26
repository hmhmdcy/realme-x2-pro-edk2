from pathlib import Path
import json, os, re, subprocess, tarfile, threading, time, wave

os.umask(0o077)
out = Path('/var/lib/samurai/k178-desktop')
out.mkdir(mode=0o700)
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == Path('/var/lib/samurai/k178-runtime/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#176 ') and Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
(out / 'boot-id-private.txt').write_bytes(boot)

def command(args):
    p = subprocess.run(args, capture_output=True)
    assert p.returncode == 0, (args, p.stderr.decode(errors='replace'))
    return p.stdout.decode(errors='replace')

def pulse(args):
    return command(['su', '-s', '/bin/sh', 'cy122', '-c', 'XDG_RUNTIME_DIR=/run/user/10000 ' + args])

def cget(n):
    return re.search(r': values=(.*)', command(['amixer', '-c', '0', 'cget', "name='" + n + "'"]))[1].strip()

def cset(n, v):
    command(['amixer', '-c', '0', 'cset', "name='" + n + "'", str(v)])

def snapshot(n):
    data = dict(playback=Path('/proc/asound/card0/pcm0p/sub0/status').read_text(),
                capture=Path('/proc/asound/card0/pcm1c/sub0/status').read_text(),
                amps={a: Path('/sys/bus/i2c/devices/' + a + '/status').read_text() for a in ['1-0039', '1-003a']})
    (out / (n + '-private.json')).write_text(json.dumps(data, indent=2) + '\n')
    return data

names = ['Left Speaker Switch', 'Right Speaker Switch', 'Headphone Jack Switch', 'QUAT_MI2S_RX Audio Mixer MultiMedia1',
         'Handset Mic Switch', 'Secondary Mic Switch', 'Speaker Mic Switch', 'DMIC MUX5', 'ADC MUX5', 'CDC_IF TX5 MUX',
         'CDC_IF TX7 MUX', 'AIF1_CAP Mixer SLIM TX5', 'AIF1_CAP Mixer SLIM TX7', 'MultiMedia2 Mixer SLIMBUS_0_TX']
saved = {}; results = []
before = command(['dmesg'])
source_before = pulse('pactl -f json list sources')
(out / 'source-before-private.json').write_text(source_before)
(out / 'dmesg-before-private.txt').write_text(before)
(out / 'pulse-before-private.json').write_text(pulse('pactl -f json list sinks'))
native = json.loads(Path('/var/lib/samurai/k178-dmic0-ucm178-low24/capture-validation.json').read_text())
try:
    saved = {n:cget(n) for n in names}
    (out / 'mixer-before-private.json').write_text(json.dumps(saved,indent=2)+'\n')
    assert cget('QUAT_MI2S_RX Audio Mixer MultiMedia1') == cget('AIF1_CAP Mixer SLIM TX5') == 'on'
    assert cget('Headphone Jack Switch') == 'off'
    for speaker, frequency in [('left', 997), ('right', 1511)]:
        stimulus = Path('/var/lib/samurai/k178-dmic0-ucm178-low24') / (speaker + '-stimulus-private.wav')
        with wave.open(str(stimulus), 'rb') as w:
            assert (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (2, 2, 48000)
            frames = w.readframes(w.getnframes())
        case = speaker + '-desktop'
        path = out / (case + '-capture-private.wav')
        start = time.monotonic()
        with (out / (case + '-parecord-private.log')).open('wb') as log, (out / (case + '-capture-private.raw')).open('wb') as raw:
            pulse('pactl suspend-source alsa_input.platform-sound.HiFi__Mic__source 0')
            rec = subprocess.Popen(['su','-s','/bin/sh','cy122','-c',
                'XDG_RUNTIME_DIR=/run/user/10000 timeout -s INT -k 2 6 parecord '
                '--device=alsa_input.platform-sound.HiFi__Mic__source --raw --format=s16le --rate=48000 --channels=1 --volume=65536'],
                stdout=raw,stderr=log)
            try:
                time.sleep(.6)
                play_start = time.monotonic()
                with (out / (case + '-paplay-private.log')).open('wb') as playlog:
                    play = subprocess.Popen(['su', '-s', '/bin/sh', 'cy122', '-c',
                        'XDG_RUNTIME_DIR=/run/user/10000 paplay --device=alsa_output.platform-sound.HiFi__Speaker__sink '
                        '--volume=65536 --raw --format=s16le --rate=48000 --channels=2'],
                        stdin=subprocess.PIPE, stdout=playlog, stderr=playlog)
                    errors = []
                    def feed():
                        try:
                            play.stdin.write(frames)
                            play.stdin.close()
                        except Exception as e:
                            errors.append(str(e))
                    writer = threading.Thread(target=feed)
                    writer.start()
                    try:
                        time.sleep(.8)
                        live = snapshot(case + '-live')
                        assert 'RUNNING' in live['playback'] and 'RUNNING' in live['capture']
                        assert all('global=01' in a and 'powered=1' in a and 'muted=0' in a and 'failed=0' in a for a in live['amps'].values())
                        assert play.wait(timeout=10) == 0
                    finally:
                        if play.poll() is None:
                            play.terminate(); play.wait(timeout=3)
                        writer.join(timeout=3)
                        assert not writer.is_alive()
                    assert not errors, errors
                capture_rc = rec.wait(timeout=8)
                assert capture_rc in [0,124]
            finally:
                if rec.poll() is None:
                    rec.terminate(); rec.wait(timeout=3)
        data = (out / (case + '-capture-private.raw')).read_bytes()
        assert len(data) % 2 == 0 and len(data) >= 5 * 48000 * 2
        with wave.open(str(path),'wb') as wrapped:
            wrapped.setparams((1,2,48000,0,'NONE','not compressed')); wrapped.writeframes(data)
        with wave.open(str(path), 'rb') as w:
            capture_frames = w.getnframes()
            assert capture_frames >= 240000
        results.append(dict(case=case, speaker=speaker, frequency=frequency, target_speaker_enabled=True,
                            play_start_after_capture_seconds=play_start-start, capture_frames=capture_frames,
                            capture_input='DMIC0', playback_api='PulseAudio paplay through user session', capture_api='PulseAudio parecord through user Mic source', capture_timeout_planned=True,
                            play_returncode=0, capture_returncode=capture_rc, both_amps_live=True))
finally:
    pulse('pactl suspend-source alsa_input.platform-sound.HiFi__Mic__source 0')
    time.sleep(7)
    final = snapshot('final')
    after = command(['dmesg'])
    (out / 'dmesg-final-private.txt').write_text(after)
    (out / 'pulse-after-private.json').write_text(pulse('pactl -f json list sinks'))
source_after = pulse('pactl -f json list sources')
(out / 'source-after-private.json').write_text(source_after)
for old, new in zip(json.loads(source_before),json.loads(source_after)):
    assert (old['volume'],old['mute']) == (new['volume'],new['mute'])
report = dict(stage=178, kernel_build=176, cases=results, code=native['code'], leading_silence_seconds=.5,
              tone_peak_dbfs=-24, paplay_stream_volume=65536, global_sink_volume_not_changed=True,
              same_boot=boot == Path('/proc/sys/kernel/random/boot_id').read_bytes(),
              mixer_restored=all(cget(n) == v for n, v in saved.items()),
              final_pcm_closed=all(final[n].strip() == 'closed' for n in ['playback', 'capture']),
              final_amplifiers_off=all('global=00' in a and 'powered=0' in a and 'muted=1' in a for a in final['amps'].values()),
              taint=int(Path('/proc/sys/kernel/tainted').read_text()),
              fault_delta={n: after.count(p)-before.count(p) for n, p in {'warnings': 'WARNING:', 'dma_prepare': 'unable to prepare channel',
                           'tx_timeout': 'TX timed out', 'resume_failed': 'NGD resume failed'}.items()})
(out / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
with tarfile.open('/tmp/k178-desktop-private.tar.gz', 'w:gz') as archive:
    archive.add(out, arcname=out.name)
print(json.dumps(report), flush=True)
assert report['same_boot'] and report['mixer_restored'] and report['final_pcm_closed'] and report['final_amplifiers_off']
assert report['taint'] == 0 and all(v == 0 for v in report['fault_delta'].values())
