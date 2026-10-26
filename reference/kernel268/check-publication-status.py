"""Read GitHub's actual branch reference after failed/timed-out Git transports."""
from pathlib import Path
import json,subprocess
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel268')
q=subprocess.run(['gh','api','repos/hmhmdcy/linux/git/ref/heads/samurai-bringup','--jq','.object.sha'],capture_output=True,timeout=30)
(P/'publication-api-response-private.log').write_bytes(q.stdout+q.stderr)
assert q.returncode==0,'Remote status unavailable; do not infer a published commit'
head=q.stdout.decode().strip();assert len(head)==40 and all(c in '0123456789abcdef' for c in head)
local=json.loads((R/'kernel-commit-validation.json').read_text())['commit']
report=dict(stage=268,repository='https://github.com/hmhmdcy/linux',branch='samurai-bringup',local_commit=local,
 actual_github_branch_head=head,published=head==local,git_transport_attempts_failed_or_stalled=True,
 source_commit_and_phone_validation_retained=True)
(R/'kernel-publication-status.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
