"""Verify merged notification bodies match the tested candidate exactly."""
from pathlib import Path
import hashlib
import json
import re

ref = Path(__file__).resolve().parent
audit = ref.parent / 'charging-ui-audit-20261023'
def function(text, name):
    m = re.search(r'^static (?:int|bool|void) ' + name + r'\(', text, re.M)
    assert m, name
    opening = text.index('{', m.start()); end = opening + 1; depth = 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}'); end += 1
    return text[m.start():end]
source = (ref / 'samurai-mp2650.c').read_text()
candidate = (audit / 'candidate/samurai-mp2650.c').read_text()
receipt = json.loads((audit / 'notification-test-result.json').read_text())
assert receipt['passed']
names = ['sm_notification_locked', 'sm_poll', 'sm_resume']
for n in names: assert function(source, n) == function(candidate, n), n
header = (ref / 'charging-notify.h').read_bytes()
assert header == (audit / 'candidate/charging-notify.h').read_bytes()
assert hashlib.sha256(header).hexdigest() == receipt['tested_files']['candidate/charging-notify.h']
result = {'passed': True, 'functions_unchanged_from_tested_candidate': names,
          'tested_cases': receipt['cases'],
          'production_source_sha256': hashlib.sha256((ref / 'samurai-mp2650.c').read_bytes()).hexdigest(),
          'candidate_receipt_sha256': hashlib.sha256((audit / 'notification-test-result.json').read_bytes()).hexdigest()}
(ref / 'ui-notification-integration-result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
