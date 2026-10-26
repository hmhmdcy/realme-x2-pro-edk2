from pathlib import Path
import hashlib, json

k = Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref = Path(__file__).parent
out = Path('/mnt/e/edk2-samurai-out/kernel172')
report = json.loads((ref / 'source-validation.json').read_text())
name = 'sound/soc/qcom/samurai-audio.c'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(k / name) == report['source_sha256'][name]
(out / 'checkpatch-second-style-private.log').write_bytes((out / 'checkpatch-private.log').read_bytes())
s = (k / name).read_text()
old = 'SND_JACK_HEADSET | SND_JACK_BTN_0 | SND_JACK_BTN_1 |'
assert s.count(old) == 1
updated = s.replace(old, 'SND_JACK_HEADSET | SND_JACK_BTN_0 |')
updated = updated.replace('SND_JACK_BTN_2 | SND_JACK_BTN_3,', 'SND_JACK_BTN_1 | SND_JACK_BTN_2 | SND_JACK_BTN_3,')
assert ''.join(updated.split()) == ''.join(s.split())
(k / name).write_text(updated)
report['after_sha256'][name] = report['source_sha256'][name] = sha(k / name)
for folder in [ref,out]: (folder / 'source-validation.json').write_text(json.dumps(report, indent=2) + '\n')
