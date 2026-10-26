"""Use accessible primary mail archives after Patchew timeout and lore denial."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib
from html.parser import HTMLParser
import json
import urllib.request
import host

ROOT = Path(__file__).resolve().parent
DIRECTORY = host.PRIVATE / 'posted-solutions'
DIRECTORY.mkdir(mode=0o700, exist_ok=True)
sources = [
    ('done', 'https://lists.openwall.net/linux-kernel/2026/09/28/1471',
     '20260928121508.1404808-2-hitesh@ebytelogic.com'),
    ('reset', 'https://lists.openwall.net/linux-kernel/2026/09/28/1534',
     '20260928121508.1404808-4-hitesh@ebytelogic.com'),
    ('reset-review', 'https://lists.openwall.net/linux-kernel/2026/09/28/1669',
     '15ab286e-23d5-46c2-a952-0be1d93409ad@linaro.org')]


class Pre(HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.text = []

    def handle_starttag(self, tag, attrs):
        if tag == 'pre':
            self.depth += 1

    def handle_endtag(self, tag):
        if tag == 'pre':
            self.depth -= 1

    def handle_data(self, data):
        if self.depth:
            self.text.append(data)


def fetch(row):
    name, url, message_id = row
    path = DIRECTORY / (name + '-mail-private.html')
    if not path.exists():
        path.write_bytes(urllib.request.urlopen(url, timeout=20).read())
    data = path.read_bytes()
    parser = Pre()
    parser.feed(data.decode())
    text = ''.join(parser.text)
    assert 'vfe' in text.lower() and ('diff --git ' in text or 'This method should be void' in text)
    (DIRECTORY / (name + '-mail-private.patch')).write_text(text)
    return dict(name=name, url=url, message_id=message_id, bytes=len(data),
                html_sha256=hashlib.sha256(data).hexdigest(),
                decoded_text_sha256=hashlib.sha256(text.encode()).hexdigest())


with ThreadPoolExecutor(max_workers=3) as pool:
    records = list(pool.map(fetch, sources))
report = dict(stage=282, author='Hitesh Patel', posted_version=5, sources=records,
    sources_read_not_executed=True, upstream_acceptance_not_verified=True,
    earlier_download_failures=['Patchew WSL urllib read timeout',
                               'Patchew Windows curl timeout with zero bytes',
                               'lore raw HTTP403; no patch downloaded'],
    applicability={'1':'Applicable: bus DONE still gated on unrelated top bit9.',
                   '2':'Already fixed in local279: vfe_get_output_v2 and RDI n/client n.',
                   '3':'Applicable: current stop still resets whole VFE for each line.',
                   '4':'Unused skip-frame query can be removed while adapting common code.',
                   '5':'Bridge transmitter discovery differs; not imported in this change.',
                   '6':'Bridge per-endpoint links differ; not imported in this change.'},
    maintainer_review='Make stop-only helper void; decrement and last reset under stream_lock.')
(ROOT / 'existing-solutions-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
