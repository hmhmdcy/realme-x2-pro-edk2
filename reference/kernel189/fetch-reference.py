"""Pin the related-device tree and fetch only relevant public engineering sources."""
from pathlib import Path
import hashlib,json,re,urllib.request

ref=Path(__file__).resolve().parent
dest=Path('/mnt/e/edk2-samurai-out/kernel189/hotdog-reference');dest.mkdir(parents=True,exist_ok=True)
base='https://api.github.com/repos/Sr-0w/hotdog-linux-bringup'
def fetch(url):
 return urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Samurai-Linux-bringup'}),timeout=30).read()
commit=json.loads(fetch(base+'/commits/main'))['sha']
tree=json.loads(fetch(base+'/git/trees/'+commit+'?recursive=1'))
assert not tree.get('truncated')
(dest/'tree.json').write_text(json.dumps(tree))
paths=[i['path'] for i in tree['tree'] if i['type']=='blob' and any(k in i['path'].lower() for k in ['fastrpc','hexagonrpc','slpi','suspend','proxy-pd','proxy-power'])]
files=[]
for name in paths:
 if not name.endswith(('.patch','.md','.c','.h','.sh','.py','.conf','.initd','.json','.service')):continue
 url='https://raw.githubusercontent.com/Sr-0w/hotdog-linux-bringup/'+commit+'/'+name
 raw=fetch(url);p=dest/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
 files.append(dict(path=name,sha256=hashlib.sha256(raw).hexdigest(),url=url,bytes=len(raw)))
report=dict(commit=commit,relevant_files=files,all_tree_paths_matching=paths)
(ref/'related-device-source-reference.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(commit=commit,files=[i['path'] for i in files])))
