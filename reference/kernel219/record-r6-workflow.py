from pathlib import Path
import json
private=Path('/mnt/e/edk2-samurai-out/kernel219');p=private/'current-work-private.json';r=json.loads(p.read_text())
r.update(prepared_followup_workflow=[
 'Wait existing exec session40635; inspect full-r6-build-private.log if it fails, no fresh abuild all replay',
 'inspect-full-features.py already passed; collect-forward-packages.py then host-runtime-qa.py (all13 APKs,5 IPA signatures, original features)',
 'stage-r6-packages.py (strict64K transfer, full isolated runtime, actual7r5 rollback verification)',
 'verify-r6-captures.py isolated-r6 (4MP default plus scoped16MP,8 finite captures, finally N/WP)',
 'native-r6-preflight.py then install-r6-packages.py; inspect transaction marker before any recovery/retry',
 'reload-wireplumber.py; verify-r6-captures.py installed-r6; run-standard-r6-client.py cam and gstreamer',
 'final-health.py; promote-r6-recipes.py; update current docs, package READMEs, archive native evidence, mirror copy-only and compare clean',
 'Full peripheral goal still active; no completion/blocked status'],
 public_kernel_patch_chain_replay_verified=True,canonical_kernel_still216=True,
 mirror_last_session=48539,mirror_last_result='3 drift/missing files due edits during copy; rerun once public files stable, do not claim clean')
p.write_text(json.dumps(r,indent=2)+'\n');print('Current r6 build and prepared verification workflow recorded privately')
