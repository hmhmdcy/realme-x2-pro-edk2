"""Launch exactly one fresh, bounded GATT transaction over authenticated SSH."""
from pathlib import Path
import json
import subprocess
import time
from host import PRIVATE, ssh

root=Path(__file__).resolve().parent
result_path=PRIVATE/'gatt-r1-private.json'
assert not result_path.exists(), 'Inspect the terminal transaction; do not replay it'
peer_path=PRIVATE/'windows-peer-private.json'
peer=json.loads(peer_path.read_text(encoding='utf-8-sig'))
assert not peer['terminal'] and peer['advertising_status'] in ['Started','StartedWithoutAllAdvertisementData']
assert 0 <= time.time()-peer_path.stat().st_mtime < 5, 'A live peer must be updating its state'
try:
    result=ssh('python3 -',input=(root/'native-gatt-client.py').read_bytes(),timeout=150)
except subprocess.CalledProcessError as error:
    result=error
result_path.write_bytes(result.stdout or b'')
(PRIVATE/'gatt-r1-stderr-private.log').write_bytes(result.stderr or b'')
data=json.loads(result.stdout)
summary={k:v for k,v in data.items() if k not in ['peer_path_private','failure','cleanup_errors']}
summary['cleanup_error_count']=len(data['cleanup_errors'])
summary['real_windows_ble_peer']=True
summary['not_a_pairing_audio_or_sco_test']=True
(root/'gatt-r1-validation.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
raise SystemExit(result.returncode)
