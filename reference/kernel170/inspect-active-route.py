from pathlib import Path
import json, math, os, re, struct, subprocess, tarfile, time, wave

os.umask(0o077)
out = Path('/var/lib/samurai/k170-active-route')
out.mkdir(mode=0o700)
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == Path('/var/lib/samurai/k169-final/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#168 ')
assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
(out / 'boot-id-private.txt').write_bytes(boot)

def command(args):
    p = subprocess.run(args, capture_output=True)
    assert p.returncode == 0, (args, p.stderr.decode(errors='replace'))
    return p.stdout.decode(errors='replace')

def pulse(args):
    return command(['su', '-s', '/bin/sh', 'cy122', '-c',
                    'XDG_RUNTIME_DIR=/run/user/10000 ' + args])

def cget(name):
    text = command(['amixer', '-c', '0', 'cget', "name='" + name + "'"])
    return re.search(r': values=(.*)', text)[1].strip()

def cset(name, value):
    command(['amixer', '-c', '0', 'cset', "name='" + name + "'", str(value)])

asoc = Path('/sys/kernel/debug/asoc/Realme X2 Pro')
selected = [
    'MultiMedia1/state',
    'dapm/Left Speaker', 'dapm/Right Speaker',
    '17300000.remoteproc:glink-edge:apr:service@7:dais/dapm/MM_DL1',
    '17300000.remoteproc:glink-edge:apr:service@8:routing/dapm/QUAT_MI2S_RX Audio Mixer',
    '17300000.remoteproc:glink-edge:apr:service@4:dais/dapm/Quaternary MI2S Playback',
    'max98937-samurai.1-0039/dapm/Left Amp',
    'max98937-samurai.1-003a/dapm/Right Amp',
]

def snapshot(name):
    data = dict(playback_status=Path('/proc/asound/card0/pcm0p/sub0/status').read_text(),
                playback_hw_params=Path('/proc/asound/card0/pcm0p/sub0/hw_params').read_text(),
                dapm={p: (asoc / p).read_text() for p in selected},
                amps={a: Path('/sys/bus/i2c/devices/' + a + '/status').read_text()
                      for a in ['1-0039', '1-003a']},
                registers={a: Path('/sys/kernel/debug/regmap/' + a + '/registers').read_text()
                           for a in ['1-0039', '1-003a']})
    (out / (name + '-private.json')).write_text(json.dumps(data, indent=2) + '\n')
    return data

tone = out / 'stereo-low36-private.wav'
amplitude = round(32767 * 10 ** (-36 / 20))
data = bytearray()
for i in range(4 * 48000):
    t = i / 48000
    fade = max(0, min(1, t / .01, (4 - t) / .01))
    data.extend(struct.pack('<hh',
                            round(amplitude * fade * math.sin(2 * math.pi * 997 * t)),
                            round(amplitude * fade * math.sin(2 * math.pi * 1511 * t))))
with wave.open(str(tone), 'wb') as w:
    w.setparams((2, 2, 48000, 0, 'NONE', 'not compressed'))
    w.writeframes(data)

names = ['Left Speaker Switch', 'Right Speaker Switch', 'Headphone Jack Switch',
         'QUAT_MI2S_RX Audio Mixer MultiMedia1']
saved = {}
before = command(['dmesg'])
(out / 'dmesg-before-private.txt').write_text(before)
try:
    pulse('pactl suspend-sink alsa_output.platform-sound.HiFi__Speaker__sink 1')
    time.sleep(.5)
    saved = {n: cget(n) for n in names}
    for n, v in zip(names, [1, 1, 0, 1]):
        cset(n, v)
    with (out / 'aplay-private.log').open('wb') as log:
        play = subprocess.Popen(['aplay', '-q', '-D', 'hw:0,0', str(tone)], stdout=log, stderr=log)
        try:
            time.sleep(.8)
            first = snapshot('live-first')
            time.sleep(.8)
            second = snapshot('live-second')
            assert play.wait(timeout=8) == 0
        finally:
            if play.poll() is None:
                play.terminate()
                play.wait(timeout=3)
finally:
    for n, v in saved.items():
        cset(n, v)
    pulse('pactl suspend-sink alsa_output.platform-sound.HiFi__Speaker__sink 0')
    time.sleep(7)
    final = snapshot('final')
    after = command(['dmesg'])
    (out / 'dmesg-final-private.txt').write_text(after)

def hw_ptr(s):
    return int(re.search(r'hw_ptr\s*:\s*(\d+)', s)[1])

registers = {a: {k: v for k, v in re.findall(r'^([0-9a-f]+): ([0-9a-f]+)$', text, re.M)}
             for a, text in first['registers'].items()}
addresses = ['018', '023', '024', '025', '026', '027', '028', '029', '036', '039', '03a', '03b', '04e', '500']
report = dict(stage=170, kernel_build=168, same_boot_as_k169_final=boot == Path('/proc/sys/kernel/random/boot_id').read_bytes(),
              tone_peak_dbfs=-36, playback_running_twice=all('RUNNING' in x['playback_status'] for x in [first, second]),
              playback_hw_ptr_advance=hw_ptr(second['playback_status']) - hw_ptr(first['playback_status']),
              hardware_params=first['playback_hw_params'],
              live_dapm=first['dapm'], live_amp_status=first['amps'],
              live_selected_amp_registers={a: {k: r[k] for k in addresses} for a, r in registers.items()},
              mixer_restored=all(cget(n) == v for n, v in saved.items()),
              final_pcm_closed=final['playback_status'].strip() == 'closed',
              final_amplifiers_off=all('global=00' in s and 'powered=0' in s and 'muted=1' in s for s in final['amps'].values()),
              taint=int(Path('/proc/sys/kernel/tainted').read_text()),
              fault_delta={n: after.count(p) - before.count(p) for n, p in {'warnings': 'WARNING:', 'dma_prepare': 'unable to prepare channel',
                           'tx_timeout': 'TX timed out', 'resume_failed': 'NGD resume failed'}.items()},
              physical_i2s_waveform_and_sound_not_proven=True)
(out / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
with tarfile.open('/tmp/k170-active-route-private.tar.gz', 'w:gz') as archive:
    archive.add(out, arcname=out.name)
print(json.dumps(report), flush=True)
assert report['same_boot_as_k169_final'] and report['playback_running_twice'] and report['playback_hw_ptr_advance'] > 0
assert report['mixer_restored'] and report['final_pcm_closed'] and report['final_amplifiers_off']
assert report['taint'] == 0 and all(v == 0 for v in report['fault_delta'].values())
