"""Narrow additive patch over frozen DWC R2; no shared source mutation."""
from pathlib import Path
import difflib
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'apsd-dwc-window-candidate-r2'
EXPECTED = '1dc9c1961a0c0b74f42c65c739702e305b9378fcbea9a348d1e73e97fd72b846'

def function(source, name):
    start = re.search(r'^static int ' + name + r'\(', source, re.M).start()
    brace = source.index('{', start)
    depth = 1
    pos = brace + 1
    while depth:
        depth += (source[pos] == '{') - (source[pos] == '}')
        pos += 1
    return source[start:pos] + '\n'

def main():
    raw = (BASE / 'core.c').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == EXPECTED
    original = raw.decode()
    old = function(original, 'dwc3_resume_common')
    assert old.count('dwc3_gadget_resume(dwc);') == 2
    new = old.replace('\t\tdwc3_gadget_resume(dwc);',
                      '\t\tret = dwc3_gadget_resume(dwc);\n\t\tif (ret)\n\t\t\tgoto out;', 1)
    new = new.replace('\t\t\tdwc3_gadget_resume(dwc);',
                      '\t\t\tret = dwc3_gadget_resume(dwc);\n\t\t\tif (ret)\n\t\t\t\tgoto out;', 1)
    assert new.count('ret = dwc3_gadget_resume(dwc);') == 2
    changed = original.replace(old, new, 1)
    (HERE / 'core.c').write_text(changed)
    (HERE / 'original-resume.inc').write_text(old)
    (HERE / 'candidate-resume.inc').write_text(new)
    patch = ''.join(difflib.unified_diff(original.splitlines(True), changed.splitlines(True),
                    fromfile='a/drivers/usb/dwc3/core.c', tofile='b/drivers/usb/dwc3/core.c'))
    (HERE / 'resume-error.patch').write_text(patch)
    report = {'base_core_sha256': EXPECTED,
              'base_revision': 'apsd-dwc-window-candidate-r2',
              'changed_function': 'dwc3_resume_common',
              'candidate_core_sha256': hashlib.sha256(changed.encode()).hexdigest(),
              'patch_sha256': hashlib.sha256(patch.encode()).hexdigest(),
              'phone_accessed': False, 'shared_source_changed': False}
    (HERE / 'source-result.json').write_text(json.dumps(report, indent=2) + '\n')

if __name__ == '__main__':
    main()
