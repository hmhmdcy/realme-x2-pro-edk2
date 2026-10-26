"""Only a newly found actual parser boundary; no author import/entry or old tests."""
from pathlib import Path
import ast
import hashlib
import json
import re

HERE=Path(__file__).resolve().parent
REF=HERE.parents[1]
SOURCE=REF/'charging-oem-audit-20261023/irq-cohort-postboot-readonly/irq-evidence.py'
raw=SOURCE.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='1e17cd3f440d71dfd223a24889cbc18453777be3a7b38b1751e6ff114990a362'
tree=ast.parse(raw)
node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='parse_interrupts')
ns={'re':re,'NAMES':('usbin-plugin','usbin-src-change')}
exec(compile(ast.Module(body=[node],type_ignores=[]),str(SOURCE),'exec'),ns)
base=' CPU0 CPU1\n47: 0 0 pmic_arb 135940 Edge usbin-plugin\n48: 0 0 pmic_arb 135942 Edge usbin-src-change\n'
bad=base+'49: 0 0 GICv3 123 Level usbin-plugin, unrelated-action\n'
accepted=ns['parse_interrupts'](bad)
assert set(accepted['named'])==set(ns['NAMES'])
control_rejected=False
try:ns['parse_interrupts'](base+'49: 0 0 GICv3 123 Level unrelated-action, usbin-plugin\n')
except ValueError:control_rejected=True
assert control_rejected
result=dict(counterexample_reproduced=True,source_sha256=hashlib.sha256(raw).hexdigest(),
 function_sha256=hashlib.sha256(ast.get_source_segment(raw.decode(),node).encode()).hexdigest(),
 actual_input=bad,actual_accepted=accepted,
 expected='reject: another IRQ action list contains exact usbin-plugin, with a shared partner',
 existing_last_position_control_rejected=control_rejected,
 author_entry_or_module_imported=False,old_27_or_other_suites_run=False,
 physical_delivery_claimed=False,device_access=False)
(HERE/'shared-action-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(counterexample_reproduced=True,control_rejected=True,
                     result_sha256=hashlib.sha256((HERE/'shared-action-result.json').read_bytes()).hexdigest())))
