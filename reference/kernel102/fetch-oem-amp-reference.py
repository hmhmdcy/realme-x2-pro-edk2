from pathlib import Path
import hashlib,json,urllib.request
repo='realme-kernel-opensource/realmeX2Pro-kernel-source'
base='https://api.github.com/repos/'+repo
out=Path('/mnt/e/edk2-samurai-out/kernel102')
dest=Path('/home/cy122/x2pro-linux/refs/realme-amp-k102')
assert not dest.exists()
def api(url):
    req=urllib.request.Request(url,headers={'User-Agent':'samurai-audio-bringup','Accept':'application/vnd.github+json'})
    with urllib.request.urlopen(req,timeout=20) as r:
        assert r.status==200 and r.url==url
        return json.load(r)
meta=api(base);branch=meta['default_branch']
commit=api(base+'/commits/'+branch)['sha']
tree=api(base+'/git/trees/'+commit+'?recursive=1')
assert not tree['truncated']
paths=[x['path'] for x in tree['tree'] if x['type']=='blob' and 'max989' in x['path'].lower() and x['path'].startswith('audio-kernel/')]
assert paths, 'No official custom amplifier source found'
dest.mkdir()
files=[]
for path in paths:
    url='https://raw.githubusercontent.com/'+repo+'/'+commit+'/'+path
    with urllib.request.urlopen(url,timeout=20) as r:
        assert r.status==200 and r.url==url
        data=r.read(2*1024*1024+1)
    assert len(data)<=2*1024*1024 and (b'GNU General Public License' in data[:2500] or b'SPDX-License-Identifier: GPL' in data[:1000])
    p=dest/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    files.append(dict(path=path,url=url,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
report=dict(primary_repository=repo,commit=commit,default_branch=branch,downloaded_files=files)
(out/'oem-amp-reference-provenance.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(commit=commit,files=[f['path'] for f in files])))
