from pathlib import Path
import hashlib,json,subprocess,sys,tempfile
root=Path(__file__).resolve().parent
manifest=json.loads((root/'manifest.json').read_text())
for item in manifest['files']:
    raw=(root/item['path']).read_bytes()
    assert len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256'],item['path']
assert hashlib.sha256((root.parent/'rx59/parity-owner-2.raw').read_bytes()).hexdigest()==manifest['prior_raw_sha256']
subprocess.run([sys.executable,str(root/'verify-capture.py')],check=True)
with tempfile.TemporaryDirectory() as tmp:
    binary=Path(tmp)/'dispatch'
    subprocess.run(['gcc','-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-parameter',str(root/'candidate-dispatch-harness.c'),'-o',str(binary)],check=True)
    result=subprocess.run([str(binary)],check=True,capture_output=True,text=True)
    assert json.loads(result.stdout)==json.loads((root/'candidate-tests.json').read_text())['cases']
state=json.loads((root/'post-state.json').read_text())
assert len(state['nodes'])==3 and all(n['Status']=='OK' for n in state['nodes'])
assert not state['known_owners'] and state['temporary_values_absent'] and not state['active_eud_trace']
assert not json.loads((root/'even-launch-cancelled.json').read_text())['helper_started']
assert json.loads((root/'candidate-summary.json').read_text())['hardware_validated'] is False
print('RX60 hashes, 512 direct matches, both closes, post-state and 14 offline dispatch cases pass. No device IO.')
