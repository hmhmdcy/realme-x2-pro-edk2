from pathlib import Path
import ast

ref = Path(__file__).parent
for n in ['capture-acoustic.py','analyze-acoustic.py']:
    s = (ref.parent / 'kernel172' / n).read_text()
    s = s.replace('k172-','k173-').replace('kernel172','kernel173').replace('stage=172','stage=173')
    s = s.replace('k173-runtime','k173-source')
    ast.parse(s); (ref / n).write_text(s)
s = (ref.parent / 'kernel172/test-desktop-acoustic.py').read_text()
s = s.replace('k172-', 'k173-').replace('stage=172','stage=173')
s = s.replace('k173-runtime','k173-source').replace('dmic0-sd1-low24','dmic0-ucm173-low24')
# Capture through the ordinary PulseAudio Mic source, not root ALSA hw access.
a = s.index("        with (out / (case + '-arecord-private.log'))"); b = s.index('            try:',a)
s = s[:a] + '''        with (out / (case + '-parecord-private.log')).open('wb') as log, (out / (case + '-capture-private.raw')).open('wb') as raw:
            pulse('pactl suspend-source alsa_input.platform-sound.HiFi__Mic__source 0')
            rec = subprocess.Popen(['su','-s','/bin/sh','cy122','-c',
                'XDG_RUNTIME_DIR=/run/user/10000 timeout -s INT -k 2 6 parecord '
                '--device=alsa_input.platform-sound.HiFi__Mic__source --raw --format=s16le --rate=48000 --channels=1 --volume=65536'],
                stdout=raw,stderr=log)
''' + s[b:]
s = s.replace("assert rec.wait(timeout=8) == 0", "capture_rc = rec.wait(timeout=8)\n                assert capture_rc in [0,124]")
# The planned timeout closes raw stdout; wrap the returned sample count as WAV.
marker = "        with wave.open(str(path), 'rb') as w:"
assert marker in s
s = s.replace(marker, '''        data = (out / (case + '-capture-private.raw')).read_bytes()
        assert len(data) % 2 == 0 and len(data) >= 5 * 48000 * 2
        with wave.open(str(path),'wb') as wrapped:
            wrapped.setparams((1,2,48000,0,'NONE','not compressed')); wrapped.writeframes(data)
''' + marker)
s = s.replace('assert w.getnframes() == 288000', 'capture_frames = w.getnframes()\n            assert capture_frames >= 240000')
s = s.replace('capture_frames=288000', 'capture_frames=capture_frames')
s = s.replace('capture_returncode=0', 'capture_returncode=capture_rc')
s = s.replace("playback_api='PulseAudio paplay through user session'", "playback_api='PulseAudio paplay through user session', capture_api='PulseAudio parecord through user Mic source', capture_timeout_planned=True")
s = s.replace("playback_api='PulseAudio paplay through user session'", "playback_api='PulseAudio paplay through user session'")
s = s.replace("before = command(['dmesg'])", "before = command(['dmesg'])\nsource_before = pulse('pactl -f json list sources')\n(out / 'source-before-private.json').write_text(source_before)")
s = s.replace("    after = command(['dmesg'])", "    after = command(['dmesg'])")
marker = "report = dict(stage=173,"
s = s.replace(marker, "source_after = pulse('pactl -f json list sources')\n(out / 'source-after-private.json').write_text(source_after)\nfor old, new in zip(json.loads(source_before),json.loads(source_after)):\n    assert (old['volume'],old['mute']) == (new['volume'],new['mute'])\n" + marker)
# Verify the installed default route without forcing any mixer or jack pin.
a = s.index("    pulse('pactl suspend-source"); b = s.index("    for speaker, frequency",a)
s = s[:a] + '''    saved = {n:cget(n) for n in names}
    (out / 'mixer-before-private.json').write_text(json.dumps(saved,indent=2)+'\\n')
    assert cget('QUAT_MI2S_RX Audio Mixer MultiMedia1') == cget('AIF1_CAP Mixer SLIM TX5') == 'on'
    assert cget('Headphone Jack Switch') == 'off'
''' + s[b:]
s = s.replace("    for n, v in saved.items():\n        cset(n, v)\n", '')
ast.parse(s); (ref / 'test-desktop-duplex.py').write_text(s)
print('K173_REGRESSION_PREPARED',flush=True)
