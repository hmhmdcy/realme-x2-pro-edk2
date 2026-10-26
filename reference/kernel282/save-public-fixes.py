"""Keep the independently tested public prerequisites in their own commit."""
from pathlib import Path
import hashlib
import json
import subprocess
import host

ROOT = Path(__file__).resolve().parent
TREE = Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
git = lambda *args: subprocess.check_output(['git','-C',str(TREE),*args],text=True)
BASE = '21facb9a7941ecd0a624a9e4fccd9ae544dde7b5'
assert git('rev-parse','HEAD').strip() == BASE
assert not git('diff','--cached','--name-only')
assert json.loads((ROOT/'prereq-build-validation.json').read_text())['exit']==0
tests=json.loads((ROOT/'multistream-host-tests-validation.json').read_text())
assert len(tests['tests'])==2 and all(t['exit']==0 and not t['stderr'] for t in tests['tests'])
paths=git('diff','--name-only').splitlines()
assert set(paths)=={'drivers/media/platform/qcom/camss/camss-vfe-17x.c','drivers/media/platform/qcom/camss/camss-vfe.c'}
git('diff','--check');git('add','--',*paths)
patch=git('diff','--cached','--binary')
(ROOT/'multistream-prerequisites.patch').write_text(patch)
style=subprocess.run(['perl',str(TREE/'scripts/checkpatch.pl'),'--no-tree',str(ROOT/'multistream-prerequisites.patch')],capture_output=True,text=True)
(host.PRIVATE/'prereq-checkpatch-private.log').write_text(style.stdout+style.stderr)
assert style.returncode==0,style.stdout+style.stderr
message=host.PRIVATE/'prereq-commit-message-private.txt'
message.write_text('''media: qcom: camss: preserve concurrent streams on 17x

Rebase Hitesh Patel's posted v5 fixes for bus DONE processing and the
last-stream VFE reset onto the local multi-output framework. Process
the per-client bus status without the unrelated top bit9 gate. Stop
only the departing line and reset exactly once at the final decrement,
under stream_lock, excluding an enable until reset completes.

Follow Bryan O'Donoghue's review to make the stop-only helper void.
The fixed RDI n/client n mapping from patch2 is already present.
Board wiring, firmware and userspace are unchanged.

Link: https://lists.openwall.net/linux-kernel/2026/09/28/1471
Link: https://lists.openwall.net/linux-kernel/2026/09/28/1534
Link: https://lists.openwall.net/linux-kernel/2026/09/28/1669

Validation: parent negative control reproduces dropped bus-only DONE
and peer reset in actual driver functions. Rebased functions pass
ASan/UBSan with real pthread locks, simultaneous stops, reset/enable
exclusion, paired-WM stop and error propagation. ARM64 CAMSS W=1/-Werror
and unchanged board DTB pass. Not deployed or hardware-verified.
''')
git('commit','-F',str(message))
assert not git('status','--porcelain')
report=dict(stage=282,commit=git('rev-parse','HEAD').strip(),parent=BASE,
    branch=git('branch','--show-current').strip(),paths=paths,
    patch_sha256=hashlib.sha256(patch.encode()).hexdigest(),
    source_hashes={p:hashlib.sha256((TREE/p).read_bytes()).hexdigest() for p in paths},
    checkpatch_exit=style.returncode,checkpatch_output=style.stdout,source_clean=True,
    upstream_mail_based_not_claimed_upstream_merged=True,not_deployed=True)
(ROOT/'prereq-commit-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['source_hashes','checkpatch_output','paths']},indent=2))
