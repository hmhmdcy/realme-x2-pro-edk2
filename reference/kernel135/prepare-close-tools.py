from pathlib import Path
import ast
r=Path('/mnt/e/RealmeX2Pro edk2')
ref=r/'reference/kernel135'
t=(r/'reference/kernel134/close-host-volumes.py').read_text().replace("ref = r / 'reference/kernel134'", "ref = r / 'reference/kernel135'").replace("out = Path('/mnt/e/edk2-samurai-out/kernel134')", "out = Path('/mnt/e/edk2-samurai-out/kernel135')")
t=t.replace("assert json.loads((ref / 'display-recovery-validation.json').read_text())['phosh_phoc_and_taint_zero_verified']", "assert json.loads((ref / 'rollback-runtime-validation.json').read_text())['taint'] == 0\nassert json.loads((ref / 'rollback-health-validation.json').read_text())['fault_increments_zero']\nassert json.loads((ref / 'stable-rollback-bundle-validation.json').read_text())['matching_stable_four_artifact_hashes_fresh_verified']")
t=t.replace('K134_PRIVATE_', 'K135_PRIVATE_')
ast.parse(t)
assert not (ref/'close-host-volumes.py').exists()
(ref/'close-host-volumes.py').write_text(t)
print('K135_DISTINCT_HOST_VOLUME_CLOSE_AND_READONLY_FSCK_TOOL_READY',flush=True)
