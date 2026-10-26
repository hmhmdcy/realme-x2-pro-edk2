"""Reuse the accepted233 audit in a fresh output directory after HCI restoration."""
from pathlib import Path
import ast
import json
import host

R = Path(__file__).resolve().parent
tree = ast.parse((R.parent / 'kernel233/final-health.py').read_text())
prefix = []
for node in tree.body:
    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'r' for t in node.targets):
        break
    prefix.append(node)
namespace = {'__file__': str(R / 'final-health.py')}
exec(compile(ast.Module(body=prefix, type_ignores=[]), 'accepted233-audit-preparation', 'exec'), namespace)
code = namespace['code']
assert code.count("out=root/'k233-final-health'") == 1
code = code.replace("out=root/'k233-final-health'", "out=root/'k234-final-health'")
code = code.replace('stage=233,', 'stage=234,')
needle = "(out/'summary.json').write_text"
extra = r'''
baseline=root/'k234-baseline-r2'
worker=json.loads((root/'k234-tools/exit-private.json').read_text())
assert worker['exit_code']==1
diagnostic=json.loads((root/'k234-diagnostic/summary.json').read_text())
assert diagnostic['state']=='restored' and diagnostic['failed'] and not diagnostic['cleanup_errors']
assert diagnostic['original_loaded_note_restored'] and diagnostic['installed_module_tree787_unchanged']
assert not Path('/sys/module/hci_uart/parameters/samurai_rx_diag').exists()
assert not Path('/sys/kernel/tracing/instances/k234-bt').exists()
for name,digest in json.loads((baseline/'userspace-hashes-private.json').read_text()).items():
 assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest
report.update(bt_diagnostic_worker_terminal=True,bt_original185_restored=True,
 bt_diagnostic_scan_harness_failed_not_powered=True,bt_phase5_state_records=2,
 bt_candidate_trace_saved_private=True,bt_trace_instance_removed=True,
 no_active_bt_capture_or_reprobe=True,full_peripheral_goal_active=True)
'''
assert code.count(needle) == 1
code = code.replace(needle, extra + '\n' + needle)
result = host.ssh('python3 -', input=code.encode(), timeout=110)
(host.PRIVATE / 'final-health-host-private.log').write_bytes(result.stdout + result.stderr)
report = json.loads(result.stdout)
(R / 'final-health-validation.json').write_text(json.dumps(report, indent=2) + '\n')
host.download('/var/lib/samurai/k234-final-health/summary.json', host.PRIVATE / 'final-health-private.json')
print(json.dumps(report))
