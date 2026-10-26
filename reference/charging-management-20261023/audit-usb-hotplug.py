"""Re-audit saved observations; never replay a physical transaction."""
from pathlib import Path
import hashlib
import importlib.util
import json

ref = Path(__file__).resolve().parent
private = Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
spec = importlib.util.spec_from_file_location('audit', ref / 'usb-hotplug.py')
audit = importlib.util.module_from_spec(spec); spec.loader.exec_module(audit)
results = {}
for transaction in ['r1', 'r2', 'r3', 'r4']:
    directory = private / ('usb-hotplug-' + transaction)
    capture = directory / 'capture-private.json'
    result = audit.audit(json.loads(capture.read_text()))
    result.update(collector_sha256=hashlib.sha256((directory / 'worker.py').read_bytes()).hexdigest(),
                  private_capture_sha256=hashlib.sha256(capture.read_bytes()).hexdigest(),
                  audit_sha256=hashlib.sha256((ref / 'usb-hotplug.py').read_bytes()).hexdigest(),
                  audit_revision=2,
                  audit_change='Physical SDP acceptance requires a complete validated physical cycle')
    prior = json.loads((ref / ('usb-hotplug-' + transaction + '-result.json')).read_text())
    result['worker_exited'] = prior['worker_exited']
    (ref / ('usb-hotplug-' + transaction + '-result.json')).write_text(json.dumps(result, indent=2) + '\n')
    results[transaction] = {k: result[k] for k in ['passed', 'physical_sdp_budget_accepted', 'detached_samples']}
(ref / 'usb-hotplug-result.json').write_text(json.dumps({'audit_revision': 2, 'transactions': results,
    'physical_cycles_accepted': ['r1', 'r2', 'r3'],
    'r4': 'Deadline without physical transition; user later reported persistent icon delay'}, indent=2) + '\n')
print(json.dumps(results, indent=2))
