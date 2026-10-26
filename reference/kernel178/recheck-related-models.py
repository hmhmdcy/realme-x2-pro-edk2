from pathlib import Path
from urllib.request import Request, urlopen
from datetime import datetime, timezone
import concurrent.futures, hashlib, json

ref = Path(__file__).resolve().parent
out = Path('E:/edk2-samurai-out/kernel178/related-model-source-private')
out.mkdir(exist_ok=True)
sha = '47087509c4289c2580c54f5433e55366b2e00445'
paths = ['docs/status.md', 'docs/evidence/2026-08-05-mainline616-internal-speakers.md',
         'docs/evidence/2026-08-05-mainline616-wcd9340.md',
         'aports/device/testing/linux-oneplus-hotdog-mainline616/0039-asoc-hotdog-enable-bounded-tfa9874-speaker-output.patch']

def fetch(path):
    url = 'https://raw.githubusercontent.com/Sr-0w/hotdog-linux-bringup/' + sha + '/' + path
    with urlopen(Request(url, headers={'User-Agent': 'samurai-audio-source-review'}), timeout=15) as r:
        data = r.read()
    target = out / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return dict(path=path, url=url, bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), fetched=True)

report = dict(stage=178, checked_utc=datetime.now(timezone.utc).isoformat(),
              repository='https://github.com/Sr-0w/hotdog-linux-bringup',
              verified_remote_head=sha, same_head_as171=True, external_code_executed=False, files=[])
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    jobs = [pool.submit(fetch, p) for p in paths]
    for path, job in zip(paths, jobs):
        try:
            report['files'].append(job.result())
        except Exception as e:
            report['files'].append(dict(path=path, fetched=False, error=str(e)))
(ref / 'related-model-provenance.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, indent=2))
