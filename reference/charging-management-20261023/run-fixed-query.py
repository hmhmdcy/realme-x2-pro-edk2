"""Run the fixed query in the agreed window, retaining raw packets privately."""
from pathlib import Path
import json
import shlex
import runpy

ref = Path(__file__).resolve().parent
ns = runpy.run_path(str(ref / 'device-window.py'))
q = ns['host'].ssh('python3 -c ' + shlex.quote((ref / 'query-fixed-telemetry.py').read_text()), timeout=35)
q.check_returncode()
data = json.loads(q.stdout)
(ns['private'] / 'fixed-query-private.json').write_bytes(q.stdout)
summary = {'mac_packets': {k: {n: v[n] for n in ['echo', 'length', 'checksum_ok', 'valid']}
                           for k, v in data['gauge'].items()},
           'short_ic': data['short_ic'], 'pmic': data['pmic'],
           'pmic_error': data.get('pmic_error'), 'configuration_data_writes': 0,
           'i2c_transfers': len(data['transactions']), 'taint_after': data['taint_after']}
(ref / 'fixed-query-result.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary, indent=2))
