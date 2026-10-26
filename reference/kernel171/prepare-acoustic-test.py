from pathlib import Path
import ast

ref = Path(__file__).parent
before = ref.parent / 'kernel170'
for name in ['capture-acoustic.py', 'analyze-acoustic.py']:
    text = (before / name).read_text().replace('k170-', 'k171-').replace('stage=170', 'stage=171')
    if name == 'capture-acoustic.py':
        text = text.replace("assert os.uname().version.startswith('#168 ')", """assert os.uname().version.startswith('#168 ')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes() == Path('/var/lib/samurai/k171-runtime/boot-id-private.txt').read_bytes()
assert Path('/sys/firmware/devicetree/base/soc@0/remoteproc@17300000/glink-edge/apr/service@4/dais/dai@16/qcom,sd-lines').read_bytes() == b'\\0\\0\\0\\1'""")
        text = text.replace("r'pin 13[789]\\b'", "r'pin (?:13[789]|140)\\b'")
        text = text.replace("assert 'RUNNING' in live['playback'] and 'RUNNING' in live['capture']", """assert 'RUNNING' in live['playback'] and 'RUNNING' in live['capture']
                            assert re.search(r'pin 140 .*function qua_mi2s', live['i2s_pinmux-pins'])""")
    ast.parse(text)
    assert not (ref / name).exists()
    (ref / name).write_text(text)
print('K171_IDENTICAL_CODED_TONE_DETECTOR_WITH_SD1_AND_FRESH_BOOT_GUARDS_PREPARED')
