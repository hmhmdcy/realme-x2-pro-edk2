"""Use the candidate core to verify the matching signed IPA module."""
from pathlib import Path
import json,subprocess
import host,storage
HERE=Path(__file__).resolve().parent
assert json.loads((HERE/'build-validation.json').read_text())['passed']
with storage.sdk_candidate():
 tree='/work/libcamera/src/libcamera-v0.7.2'
 q=subprocess.run(['chroot',str(storage.SDK),'env','LD_LIBRARY_PATH='+tree+'/output/src/libcamera',tree+'/output/src/apps/ipa-verify/ipa_verify',tree+'/output/src/ipa/camss-vfe/ipa_camss_vfe.so'],capture_output=True)
(host.PRIVATE/'signature-check.log').write_bytes(q.stdout+q.stderr)
assert not q.returncode and b'IPA module signature is valid' in q.stdout
r=dict(stage=421,candidate_core_verified_candidate_ipa_signature=True,private_ipa_version=2,sdk_bind_unmounted=True,passed=True)
(HERE/'signature-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
