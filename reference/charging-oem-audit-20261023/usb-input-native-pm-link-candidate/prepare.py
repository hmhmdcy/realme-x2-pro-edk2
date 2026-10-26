"""Source-only PM ordering delta; never touches a device or shared build."""
from pathlib import Path
import difflib, hashlib, json

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'usb-input-flat-consumer-candidate'
sha = lambda raw: hashlib.sha256(raw).hexdigest()
PINS = {
    'samurai-usb-input.c': 'ee0f0806c5a51576f10b299aca173c61ab2b4764a5954c1039d1c73327878a88',
    'samurai-usb-input-decode.h': 'a17caa2cbeb2352da249474e0265fa96745f544d96a29d0ebe8f14c656d548fd',
}

def function(text, name):
    import re
    match = re.search(r'(?m)^static [^;{}\n]+\b' + re.escape(name) + r'\s*\(', text)
    assert match, name
    start = match.start()
    brace = text.index('{', match.end())
    level = 1
    end = brace + 1
    while level:
        level += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end] + '\n'

def main():
    raws = {name: (BASE / name).read_bytes() for name in PINS}
    for name, pin in PINS.items():
        assert sha(raws[name]) == pin, name
    old = raws['samurai-usb-input.c'].decode()
    text = old.replace('#include <linux/of.h>\n', '#include <linux/of.h>\n#include <linux/of_platform.h>\n')
    assert text != old
    text = text.replace('struct samurai_usb_input {\n', '''struct samurai_usb_input {
\tstruct device *native_consumer;
\tstruct device *native_supplier;
''', 1)
    addition = (HERE / 'native-pm-link.c.inc').read_text()
    anchor = 'static int samurai_usb_probe(struct platform_device *pdev)\n'
    assert text.count(anchor) == 1
    text = text.replace(anchor, addition + '\n' + anchor)
    anchor = '\tINIT_DELAYED_WORK(&input->work, samurai_usb_poll);\n'
    assert text.count(anchor) == 1
    text = text.replace(anchor, anchor + '''\t/* Establish system-PM ordering before DWC3 can acquire this supply. */
\tret = samurai_usb_link_native_consumer(dev, input);
\tif (ret)
\t\treturn ret;
''')
    (HERE / 'samurai-usb-input.c').write_text(text, encoding='utf-8', newline='\n')
    (HERE / 'samurai-usb-input-decode.h').write_bytes(raws['samurai-usb-input-decode.h'])
    (HERE / 'native-pm-link.patch').write_text(''.join(difflib.unified_diff(
        old.splitlines(True), text.splitlines(True), fromfile='flat-ee0f/samurai-usb-input.c',
        tofile='native-pm-link/samurai-usb-input.c')), encoding='utf-8', newline='\n')
    unchanged = ['samurai_usb_read_status', 'samurai_usb_get_budget',
        'samurai_usb_get_property', 'samurai_usb_set_property', 'samurai_usb_poll',
        'samurai_usb_stop', 'samurai_usb_suspend', 'samurai_usb_resume',
        'samurai_usb_retain_for_native_consumer', 'samurai_usb_parent_match',
        'samurai_usb_init', 'samurai_usb_exit']
    for name in unchanged:
        assert function(old, name) == function(text, name), name
    names = ['samurai_usb_unlink_native_consumer', 'samurai_usb_link_native_consumer',
        'samurai_usb_probe']
    (HERE / 'actual-link-and-probe.inc').write_text('\n'.join(function(text, n) for n in names),
        encoding='utf-8', newline='\n')
    names = ['samurai_usb_set_property', 'samurai_usb_stop', 'samurai_usb_suspend', 'samurai_usb_resume']
    (HERE / 'actual-pm-and-setter.inc').write_text('\n'.join(function(text, n) for n in names),
        encoding='utf-8', newline='\n')
    core = HERE.parent / 'apsd-integration/current-r7/snapshots/drivers--usb--dwc3--core.c'
    core_raw = core.read_bytes()
    assert sha(core_raw) == 'bd8a8aabf199952717926b8ee79562e283ed9cd6a1ee485d22cd52167ad7ffcf'
    (HERE / 'actual-dwc-vbus-work.inc').write_text(function(core_raw.decode(), 'dwc3_vbus_draw_work'),
        encoding='utf-8', newline='\n')
    result = dict(passed=True, baseline={n: dict(path=str(BASE / n), sha256=p) for n,p in PINS.items()},
        source_sha256=sha((HERE / 'samurai-usb-input.c').read_bytes()),
        decoder_sha256=sha((HERE / 'samurai-usb-input-decode.h').read_bytes()),
        old_functions_byte_identical=unchanged, changed_old_function='samurai_usb_probe',
        new_functions=['samurai_usb_unlink_native_consumer', 'samurai_usb_link_native_consumer'],
        DWC_core_sha256=sha(core_raw), device_or_shared_build_accessed=False,
        new_link_flags='DL_FLAG_STATELESS only', raw_link_pointer_saved=False,
        extracts={n: sha((HERE / n).read_bytes()) for n in (
            'actual-link-and-probe.inc', 'actual-pm-and-setter.inc', 'actual-dwc-vbus-work.inc')})
    (HERE / 'source-result.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(result))

if __name__ == '__main__':
    main()
