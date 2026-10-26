from pathlib import Path
from datetime import datetime, timezone
from urllib.request import Request, urlopen
import concurrent.futures, hashlib, json

ref = Path(__file__).resolve().parent
out = Path('E:/edk2-samurai-out/kernel176/upstream-source-recheck-private')
out.mkdir(exist_ok=True)

def fetch(url):
    req = Request(url, headers={'User-Agent': 'samurai-audio-source-review'})
    with urlopen(req, timeout=15) as response:
        return response.read()

report = dict(stage=176, checked_utc=datetime.now(timezone.utc).isoformat(), sources=[], external_code_executed=False)
try:
    try:
        meta = json.loads(fetch('https://api.github.com/repos/torvalds/linux/commits/master'))
        sha = meta['sha']
    except Exception as e:
        report['commit_discovery_error'] = str(e)
        sha = 'master'
        report['branch_content_pinned_by_sha256_instead_of_commit'] = True
    paths = ['drivers/mfd/wcd934x.c', 'drivers/slimbus/core.c']
    urls = ['https://raw.githubusercontent.com/torvalds/linux/' + sha + '/' + p for p in paths]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(fetch, url) for url in urls]
        for path, url, future in zip(paths, urls, futures):
            try:
                data = future.result()
                (out / path.replace('/', '_')).write_bytes(data)
                text = data.decode()
                entry = dict(path=path, ref=sha, url=url, sha256=hashlib.sha256(data).hexdigest(), bytes=len(data), fetched=True)
                if path.startswith('drivers/mfd/'):
                    entry.update(reset_gpio_present='gpiod_set_value(reset_gpio,' in text,
                                 absent_api_used='slim_report_absent(' in text,
                                 address_query_used='slim_get_logical_addr(' in text)
                else:
                    start = text.index('void slim_report_absent(')
                    body = text[start:text.index('EXPORT_SYMBOL_GPL(slim_report_absent)', start)]
                    entry.update(absent_api_exported=True, absent_function_has_was_valid_guard='was_valid' in body)
                report['sources'].append(entry)
            except Exception as e:
                report['sources'].append(dict(path=path, url=url, fetched=False, error=str(e)))
except Exception as e:
    report['discovery_error'] = str(e)
report['both_fetched'] = len(report['sources']) == 2 and all(s['fetched'] for s in report['sources'])
(ref / 'upstream-source-recheck.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
(out / 'provenance.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, indent=2))
