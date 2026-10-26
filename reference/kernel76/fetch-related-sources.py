"""Fetch public vendor/upstream source text only; do not execute it."""
from pathlib import Path
import concurrent.futures, hashlib, json, re, urllib.request
import sys

OUT = Path('/mnt/e/edk2-samurai-out/kernel76/charging-research')
OUT.mkdir(parents=True, exist_ok=True)
REPOS = {
    'realme': 'realme-kernel-opensource/realmeX2Pro-kernel-source',
    'oppo-ace': 'oppo-source/Reno10X-RenoAce-10.0-kernel-source',
    'oneplus': 'OnePlusOSS/android_kernel_oneplus_sm8150',
    'mainline': 'torvalds/linux',
}

def read(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0 SourceResearch'}), timeout=25) as r:
        return r.read(5 * 1024 * 1024)

def metadata(html):
    oid = re.search(r'"currentOid":"([0-9a-f]{40})"', html)
    branch = re.search(r'"defaultBranch":"([^"]+)"', html)
    items = []
    for body in re.findall(r'<script[^>]*type="application/json"[^>]*>([\s\S]*?)</script>', html):
        try:
            parsed = json.loads(body)
        except ValueError:
            continue
        def walk(obj):
            if isinstance(obj, dict):
                if 'items' in obj and isinstance(obj['items'], list):
                    items.extend(x for x in obj['items'] if isinstance(x, dict) and 'path' in x)
                for v in obj.values(): walk(v)
            elif isinstance(obj, list):
                for v in obj: walk(v)
        walk(parsed)
    return {'oid': oid[1] if oid else None, 'branch': branch[1] if branch else None, 'items': [{k:x.get(k) for k in ('name','path','contentType')} for x in items]}

def root(item):
    name, repo = item
    url = 'https://github.com/' + repo
    try:
        raw = read(url)
        (OUT / (name + '-root.html')).write_bytes(raw)
        return {'name':name,'repo':repo,'url':url,'sha256':hashlib.sha256(raw).hexdigest(), **metadata(raw.decode())}
    except Exception as exc:
        return {'name':name,'repo':repo,'url':url,'error':str(exc)}

def source(item):
    name, path, kind = item
    heads = {x['name']:x for x in json.loads((OUT / 'repository-heads.json').read_text())}
    head = heads[name]
    assert head.get('oid')
    url = ('https://github.com/' + head['repo'] + '/tree/' if kind == 'tree' else 'https://raw.githubusercontent.com/' + head['repo'] + '/') + head['oid'] + '/' + path
    try:
        raw = read(url)
        dest = name + '--' + path.replace('/', '--') + ('.html' if kind == 'tree' else '')
        (OUT / dest).write_bytes(raw)
        record = {'name':name,'path':path,'kind':kind,'url':url,'commit':head['oid'],'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'saved':dest}
        if kind == 'tree':
            record['items'] = metadata(raw.decode())['items']
        else:
            lines = raw.decode(errors='replace').splitlines()
            record['matches'] = [{'line':i+1,'text':line} for i,line in enumerate(lines) if re.search(r'mp2650|bq28z610|bq27541|smb1355|SMB5|batt_num|OVERTIME_DISABLED|OPPO_CHARGER|ONEPLUS_CHARGER', line, re.I)][:35]
        return record
    except Exception as exc:
        return {'name':name,'path':path,'kind':kind,'url':url,'error':str(exc)}

if __name__ == '__main__':
    if len(sys.argv) > 1:
        tasks = json.loads((OUT / sys.argv[1]).read_text())
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            rows = list(pool.map(source, tasks))
        (OUT / (sys.argv[1] + '.results.json')).write_text(json.dumps(rows, indent=2) + '\n')
        display = []
        for row in rows:
            slim = {k:v for k,v in row.items() if k not in ('items','matches')}
            if 'items' in row:
                paths = sorted({x['path'] for x in row['items'] if x.get('path', '').rsplit('/', 1)[0] == row['path']})
                slim['child_count'] = len(paths)
                slim['relevant_children'] = [p for p in paths if re.search(r'mp26|bq27|bq28|oppo|oneplus|19781|19[0-9]{3}|sm8150|msmnile|\.dtsi$', p, re.I)][:40]
            if 'matches' in row:
                slim['matches'] = row['matches'][:12]
            display.append(slim)
        print(json.dumps(display, indent=2))
        sys.exit(0)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(root, REPOS.items()))
    (OUT / 'repository-heads.json').write_text(json.dumps(rows, indent=2) + '\n')
    print(json.dumps([{k:v for k,v in x.items() if k != 'items'} for x in rows], indent=2))
