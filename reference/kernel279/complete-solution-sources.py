"""Resolve inspected repository paths and pin the newer posted OPE v10 series."""
from pathlib import Path
import gzip
import hashlib
import json
import mailbox
import urllib.request

ROOT = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel279/existing-solutions')
LOCK = ROOT / 'existing-solutions-validation.json'
state = json.loads(LOCK.read_text())
requests = [('loicpoulain/linux', 'drivers/media/platform/qcom/camss/camss-ope.c')]
for repo, path in requests:
    row = next(row for row in state['repositories'] if row['repo'] == repo)
    url = f"https://raw.githubusercontent.com/{repo}/{row['commit']}/{path}"
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Samurai-CAMSS-audit'}), timeout=30) as reply:
        data = reply.read(4 * 1024 * 1024)
    name = repo.replace('/', '_') + '--' + path.replace('/', '__')
    (PRIVATE / name).write_bytes(data)
    row['files'][path] = dict(url=url, sha256=hashlib.sha256(data).hexdigest(), bytes=len(data), local_name=name)
    row['initial_404_paths_retained_as_history'] = True
    print(repo, path, len(data))
url = 'https://lore.kernel.org/all/20260925-camss-isp-ope-v10-0-2622411034cb@oss.qualcomm.com/t.mbox.gz'
with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'b4/0.14 Samurai-CAMSS-audit'}), timeout=35) as reply:
    data = reply.read(8 * 1024 * 1024)
assert data.startswith(b'\x1f\x8b')
raw = gzip.decompress(data)
mbox = PRIVATE / 'ope-v10.mbox'
mbox.write_bytes(raw)
box = mailbox.mbox(mbox)
subjects = [' '.join(message.get('Subject', '').split()) for message in box]
state['ope_v10'] = dict(url=url, compressed_sha256=hashlib.sha256(data).hexdigest(),
                       mbox_sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw), subjects=subjects)
state['millicam_af_6'] = dict(repo='https://gitlab.com/tui/libcamera.git',
                            ref='refs/heads/millicam_af_6', commit='4312a90e32ead12c1db1d220edd5bcbaf58f0e86',
                            evidence='git ls-remote returned this ref in stage279; not imported')
LOCK.write_text(json.dumps(state, indent=2) + '\n')
print('OPE v10 thread:', len(box), 'messages;', len(raw), 'bytes')
