"""Extract the posted RFC exactly and apply it in an isolated source candidate.

Does not touch the maintained checkout, package recipes, or handset.
Stops at the first apply failure and records the exact patch and stderr.
"""
from pathlib import Path
import email.header
import hashlib
import json
import mailbox
import re
import subprocess

ROOT = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel279')
BASE = Path('/home/cy122/x2pro-linux/camera270-kernel')
CANDIDATE = Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
PIN = '0d69276125ec8e7d0cc083ac421e2ad7fe79a3c8'
BRANCH = 'samurai-isp279-candidate'


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args],
                          capture_output=True, text=True, check=True).stdout


assert git(BASE, 'rev-parse', 'HEAD').strip() == PIN
assert not git(BASE, 'status', '--porcelain')
box = mailbox.mbox(PRIVATE / 'inline-proposal.mbox')
patch_dir = PRIVATE / 'posted-patches'
patch_dir.mkdir(exist_ok=True)
patches = []
for message in box:
    subject = str(email.header.make_header(email.header.decode_header(message['Subject'])))
    subject = ' '.join(subject.split())
    match = re.match(r'^\[PATCH (\d+)/74\]', subject)
    if not match or int(match[1]) == 0:
        continue
    number = int(match[1])
    payload = message.get_payload(decode=True)
    assert b'diff --git a/' in payload
    path = patch_dir / f'{number:02d}.patch'
    path.write_bytes(payload)
    patches.append(dict(number=number, subject=subject,
                        message_id=message['Message-ID'].strip('<>'),
                        sha256=hashlib.sha256(payload).hexdigest(),
                        bytes=len(payload)))
assert [p['number'] for p in patches] == list(range(1, 75))
assert not CANDIDATE.exists(), 'Inspect an existing candidate before resuming it'
git(BASE, 'worktree', 'add', '-b', BRANCH, str(CANDIDATE), PIN)
result = dict(stage=279, base_commit=PIN, branch=BRANCH,
              candidate=str(CANDIDATE), posted_series_is_rfc=True,
              patches=patches, applied=[], phone_unchanged=True)
for patch in patches:
    path = patch_dir / f"{patch['number']:02d}.patch"
    check = subprocess.run(['git', '-C', str(CANDIDATE), 'apply', '--check', str(path)],
                           capture_output=True, text=True)
    if check.returncode:
        result['first_conflict'] = dict(number=patch['number'], stderr=check.stderr)
        break
    git(CANDIDATE, 'apply', str(path))
    result['applied'].append(patch['number'])
(ROOT / 'inline-candidate-apply-validation.json').write_text(
    json.dumps(result, indent=2) + '\n')
print(json.dumps({k: v for k, v in result.items() if k != 'patches'}, indent=2))
