"""Pin the posted multi-camera fixes and maintainer feedback, without running source."""
from pathlib import Path
import email
import email.policy
import hashlib
from html.parser import HTMLParser
import json
import re
import urllib.parse
import urllib.request
import host

ROOT = Path(__file__).resolve().parent
directory = host.PRIVATE / 'posted-solutions'
directory.mkdir(mode=0o700, exist_ok=True)
base = 'https://patchew.org/linux/20260928121508.1404808-1-hitesh@ebytelogic.com/'


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.links += [v for k,v in attrs if k == 'href' and 'mbox' in v]


records = []
for number in range(1, 7):
    identity = '20260928121508.1404808-%d-hitesh@ebytelogic.com' % (number + 1)
    page_url = base + identity + '/'
    page_path = directory / ('patch-%d-page-private.html' % number)
    if not page_path.exists():
        page_path.write_bytes(urllib.request.urlopen(page_url, timeout=25).read())
    parser = Links()
    parser.feed(page_path.read_text())
    assert parser.links, (page_url, 'No observed mbox link')
    url = urllib.parse.urljoin(page_url, parser.links[0])
    mbox_path = directory / ('patch-%d-private.mbox' % number)
    if not mbox_path.exists():
        mbox_path.write_bytes(urllib.request.urlopen(url, timeout=25).read())
    data = mbox_path.read_bytes()
    # A Patchew per-message mbox starts with an mbox separator; the first
    # message is the requested patch, with replies possibly following it.
    messages = re.split(br'(?m)^From [^\n]+\n', data)
    parsed = [email.message_from_bytes(m, policy=email.policy.default) for m in messages if m.strip()]
    message = next(m for m in parsed if str(m['Message-ID']).strip('<>') == identity)
    body = message.get_content()
    assert 'diff --git a/drivers/media/platform/qcom/camss/' in body
    body_path = directory / ('patch-%d-private.patch' % number)
    body_path.write_text(body)
    records.append(dict(number=number, message_id=identity, subject=str(message['Subject']),
        page_url=page_url, observed_mbox_url=url, bytes=len(data),
        mbox_sha256=hashlib.sha256(data).hexdigest(), body_sha256=hashlib.sha256(body.encode()).hexdigest(),
        primary_author_post=True))
    print(json.dumps(dict(number=number, subject=str(message['Subject']), bytes=len(data))), flush=True)

report = dict(stage=282, series='20260928121508.1404808-1-hitesh@ebytelogic.com',
    posted_version=5, patches=records, sources_read_not_executed=True,
    upstream_acceptance_not_verified=True,
    reset_review_url='https://lists.openwall.net/linux-kernel/2026/09/28/1669',
    reset_review='Maintainer requests void stop helper; reset and final decrement remain under stream_lock.',
    applicability={'1':'Applicable: parent still gates bus DONE on unrelated top IRQ bit9.',
                   '2':'Already implemented in local279: fixed RDI n to client n.',
                   '3':'Applicable: parent still resets whole VFE on every line stop.',
                   '4':'Unused skip-frame query remains; remove with common enable changes.',
                   '5':'CSI bridge topology differs from this board; evaluate separately, not needed for fixed FULL DMA.',
                   '6':'CSI bridge endpoint linking differs; not required for current point-to-point sensors.'})
(ROOT / 'existing-solutions-validation.json').write_text(json.dumps(report, indent=2) + '\n')
