from pathlib import Path
import json, shutil, tarfile

ref = Path(__file__).parent
out = Path('/mnt/e/edk2-samurai-out/kernel173')
with tarfile.open(out/'k173-final-policy-private.tar.gz') as archive:
    final = json.load(archive.extractfile('k173-final-policy/validation.json'))
assert final['live_port_switch_policy_loaded'] and final['installed_ucm173_verified'] and final['single_pulse_card_and_alsa_module']
assert final['taint']==0 and all(v==0 for v in final['fault_counts'].values())
assert final['final_amplifiers_off'] and final['nv_verified'] and final['modules132_verified']
shutil.copyfile(ref/'final-validation.json',ref/'final-validation-before-policy.json')
(ref/'final-validation.json').write_text(json.dumps(final,indent=2)+'\n')
print('K173_POLICY_FINAL_SUMMARIZED',flush=True)
