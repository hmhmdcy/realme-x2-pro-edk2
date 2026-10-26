"""Read-only source research. Never connects to the phone or writes registers."""
from pathlib import Path
import concurrent.futures, hashlib, json, subprocess, urllib.request
import re

OUT = Path('/mnt/e/edk2-samurai-out/kernel76/charging-research')
OUT.mkdir(parents=True, exist_ok=True)
HEADERS = {'User-Agent': 'Linux-charging-source-research', 'Accept': 'application/vnd.github+json'}
URLS = {
    'realme-repos': 'https://api.github.com/orgs/realme-kernel-opensource/repos?per_page=100',
    'oneplus-repos': 'https://api.github.com/orgs/OnePlusOSS/repos?per_page=100',
    'oppo-repos': 'https://api.github.com/orgs/oppo-source/repos?per_page=100',
    'mainline-tree': 'https://api.github.com/repos/torvalds/linux/contents/drivers/power/supply',
}
WEB_URLS = {
    'search-realme-mp2650': 'https://www.google.com/search?q=realme+X2+Pro+mp2650+kernel+github',
    'search-renoace-mp2650': 'https://www.google.com/search?q=Reno+Ace+mp2650+kernel+github',
    'search-mainline-mp2650': 'https://www.google.com/search?q=MP2650+Linux+mainline+driver',
    'realme-repository': 'https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source',
    'oneplus-repository': 'https://github.com/OnePlusOSS/android_kernel_oneplus_sm8150',
    'oppo-repositories': 'https://github.com/orgs/oppo-source/repositories?q=Ace',
}

def fetch(item):
    name, url = item
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=25) as response:
            raw = response.read()
            status = response.status
        (OUT / (name + '.json')).write_bytes(raw)
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            if name == 'mainline-tree':
                rows = [x.get('name') for x in parsed if any(n in x.get('name', '').lower() for n in ('mp26', 'bq27', 'bq28', 'qcom'))]
            else:
                rows = [{k: x.get(k) for k in ('full_name', 'html_url', 'default_branch', 'pushed_at')} for x in parsed if any(n in x.get('name', '').lower() for n in ('8150', '855', 'x2', '1931', 'ace'))]
        else:
            rows = parsed
        return dict(name=name, url=url, status=status, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), matches=rows)
    except Exception as exc:
        return dict(name=name, url=url, error=str(exc))

def fetch_web(item):
    name, url = item
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; SourceResearch/1.0)'})
        with urllib.request.urlopen(request, timeout=25) as response:
            raw = response.read(5 * 1024 * 1024)
            status = response.status
        (OUT / (name + '.html')).write_bytes(raw)
        html = raw.decode(errors='replace')
        matches = re.findall(r'.{0,150}(?:mp2650|bq28z610|RenoAce|Reno_Ace|defaultBranch|default_branch|currentOid|android_kernel_oneplus_sm8150|realmeX2Pro-kernel-source).{0,250}', html, flags=re.I)
        links = list(dict.fromkeys(re.findall(r'https://github.com/[^\s<>"&]+', html)))[:30]
        return dict(name=name, url=url, status=status, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), matches=matches[:14], links=links)
    except Exception as exc:
        return dict(name=name, url=url, error=str(exc))

if __name__ == '__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(fetch_web, WEB_URLS.items()))
    vendor = '/mnt/e/Realme X2 Pro移植主线Linux/sources/realme-downstream.git'
    remote = subprocess.check_output(['git', '--git-dir=' + vendor, 'config', '--get', 'remote.origin.url']).decode().strip()
    record = dict(vendor_remote=remote, results=results)
    (OUT / 'discovery.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record, indent=2))
