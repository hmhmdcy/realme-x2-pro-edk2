"""Create the single-function delta from the exact installed501 gauge source."""
from pathlib import Path
import difflib
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1] / 'charging-oem-audit-20261023/gauge-current-samurai-candidate/bq27xxx_battery.c'
sha = lambda b: hashlib.sha256(b).hexdigest()
original = BASE.read_bytes()
assert sha(original) == '0aa3c533bab0ec9219364af5328d353334cbf5112f97c8529aa162f95fd88ffe'
old = b'\t/* After charger plug in/out wait 0.5s for things to stabilize */\n\tmod_delayed_work(system_percpu_wq, &di->work, HZ / 2);'
new = b'\t/* Native instantaneous status needs no average-current settling delay.\n\t * Other chips and opt-out profiles retain the original 0.5s wait.\n\t */\n\tmod_delayed_work(system_percpu_wq, &di->work,\n\t\t\t bq27xxx_samurai_instant(di) ? 0 : HZ / 2);'
assert original.count(old) == 1
candidate = original.replace(old, new)
assert candidate.replace(new, old) == original
(HERE / 'bq27xxx_battery.c').write_bytes(candidate)
patch = ''.join(difflib.unified_diff(original.decode().splitlines(True), candidate.decode().splitlines(True),
                                   'a/drivers/power/supply/bq27xxx_battery.c', 'b/drivers/power/supply/bq27xxx_battery.c'))
(HERE / 'notify-immediate.patch').write_bytes(patch.encode())
gate = re.search(r'static bool bq27xxx_samurai_instant\(.*?\n\}', candidate.decode(), re.S)[0]
callback = re.search(r'static void bq27xxx_external_power_changed\(.*?\n\}', candidate.decode(), re.S)[0]
assert gate in original.decode()
(HERE / 'actual-functions.inc').write_bytes((gate + '\n\n' + callback + '\n').encode())
receipt = {'base_source_sha256': sha(original), 'candidate_source_sha256': sha(candidate),
           'patch_sha256': sha(patch.encode()), 'only_function_changed': 'bq27xxx_external_power_changed',
           'reverse_replacement_equals_501_base': True, 'original_strict_gate_byte_equal': True,
           'actual_functions_sha256': sha((gate + '\n\n' + callback + '\n').encode()),
           'prepare_sha256': sha(Path(__file__).read_bytes()), 'installed': False}
(HERE / 'source-result.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
