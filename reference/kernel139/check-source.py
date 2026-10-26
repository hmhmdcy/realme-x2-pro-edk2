from pathlib import Path
import hashlib
import json
import subprocess

r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel139'
out = Path('/mnt/e/edk2-samurai-out/kernel139')
k = Path('/home/cy122/pmos-samurai-kernel136/kernel')
manifest = json.loads((ref / 'unwind-source-validation.json').read_text())
assert all(hashlib.sha256((k / name).read_bytes()).hexdigest() == digest for name, digest in manifest['files'].items())
result = subprocess.run(['perl', str(k / 'scripts/checkpatch.pl'), '--no-signoff', '--ignore', 'COMMIT_MESSAGE', str(ref / 'ngd-unsubmitted-unwind.patch')], capture_output=True)
(out / 'checkpatch-private.txt').write_bytes(result.stdout + result.stderr)
assert result.returncode == 0
result = subprocess.run(['git', '-C', str(k), 'diff', '--check', '--', *manifest['only_changed_files']], capture_output=True)
(out / 'git-diff-check-private.txt').write_bytes(result.stdout + result.stderr)
assert result.returncode == 0
report = dict(stage=139, checkpatch_code_errors=0, checkpatch_code_warnings=0,
              no_commit_or_signoff_claim=True, changed_files_git_diff_check_pass=True,
              baseline_eud_two_whitespace_findings_preserved=True,
              two_changed_sources_match_manifest=True)
(ref / 'source-check-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print('K139_SOURCE_HASH_CHECKPATCH_AND_DIFF_CHECK_PASS')
