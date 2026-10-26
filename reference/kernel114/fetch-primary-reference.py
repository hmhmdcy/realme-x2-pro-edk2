from pathlib import Path
import hashlib, json, urllib.request

out=Path('/mnt/e/edk2-samurai-out/kernel114/primary-reference')
out.mkdir(exist_ok=False)
base='https://api.github.com/repos/Sr-0w/hotdog-linux-bringup'
def fetch(url):
    request=urllib.request.Request(url, headers={'User-Agent':'samurai-port-research'})
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read()
commit=json.loads(fetch(base+'/commits/main'))['sha']
tree=fetch(base+'/git/trees/'+commit+'?recursive=1')
(out/'tree.json').write_bytes(tree)
entries=json.loads(tree)['tree']
selected=[p['path'] for p in entries if p['type']=='blob' and (
    'ipa' in p['path'].lower() or
    p['path'] in ['docs/status.md','README.md'] or
    ('patches/' in p['path'] and any(s in p['path'].lower() for s in ['dpu','dsi','sensor','camss','ubwc'])))]
records=[]
for path in selected:
    url=f'https://raw.githubusercontent.com/Sr-0w/hotdog-linux-bringup/{commit}/{path}'
    data=fetch(url)
    dest=out/path
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(data)
    records.append(dict(path=path,url=url,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
report=dict(repository='https://github.com/Sr-0w/hotdog-linux-bringup',commit=commit,files=records,foreign_device_configuration_not_deployed=True)
(out/'source-manifest.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(commit=commit,files=len(records),ipa_paths=[p for p in selected if 'ipa' in p.lower()]),indent=2))
