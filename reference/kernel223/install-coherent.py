from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
assert json.loads((here/'control-snapshot-native-validation.json').read_text())['capture_time_control_snapshots_verified']
p=host.ssh('python3 -',input=(here/'native-coherent-install.py').read_bytes(),timeout=180)
(host.PRIVATE/'coherent-install-host-private.log').write_bytes(p.stdout+p.stderr)
r=json.loads(p.stdout);(here/'coherent-install-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
