from pathlib import Path
import hashlib, json

k = Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref = Path(__file__).parent
out = Path('/mnt/e/edk2-samurai-out/kernel172')
report = json.loads((ref / 'source-validation.json').read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
for n, digest in report['source_sha256'].items(): assert sha(k / n) == digest
(out / 'checkpatch-first-style-private.log').write_bytes((out / 'checkpatch-private.log').read_bytes())
for name, start, end, match in [
    ('sound/soc/qcom/samurai-audio.c', 'static int samurai_setup_jack', 'static int samurai_fixup', 'ret = snd_soc_card_jack_new_pins('),
    ('sound/soc/codecs/wcd934x.c', 'static int wcd934x_init_dmic', 'static int wcd934x_hw_init', 'ret = snd_soc_component_update_bits('),
]:
    s = (k / name).read_text(); a = s.index(start); b = s.index(end, a)
    lines = s[a:b].splitlines(True); indent = None
    for i, line in enumerate(lines):
        if match in line:
            column = line.expandtabs(8).index('(') + 1
            indent = '\t' * (column // 8) + ' ' * (column % 8)
        elif indent is not None:
            lines[i] = indent + line.lstrip()
            if line.rstrip().endswith(';'): indent = None
    updated = s[:a] + ''.join(lines) + s[b:]
    assert ''.join(s.split()) == ''.join(updated.split())
    (k / name).write_text(updated)
report['after_sha256'] = {n:sha(k / n) for n in report['modified_this_stage']}
report['source_sha256'] = {n:sha(k / n) for n in report['tracked_modified_files']}
report['checkpatch_alignment_repair_only'] = True
for folder in [ref,out]: (folder / 'source-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print('CHECKPATCH_ALIGNMENT_REPAIRED', flush=True)
