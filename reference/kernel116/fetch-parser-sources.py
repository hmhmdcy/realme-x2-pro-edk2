from pathlib import Path
import urllib.request,json,hashlib
out=Path('/mnt/e/edk2-samurai-out/kernel117');out.mkdir(exist_ok=False)
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel117');ref.mkdir(exist_ok=False)
def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':'samurai-camera-research'})
    with urllib.request.urlopen(req,timeout=45) as r:return r.read()
records=[]
for repo,branch in [('armijnhemel/binaryanalysis-ng','master'),('bjzhou/CamxChi','main')]:
    api='https://api.github.com/repos/'+repo
    commit=json.loads(fetch(api+'/commits/'+branch))['sha']
    directory=out/repo.split('/')[-1];directory.mkdir()
    tree=fetch(api+'/git/trees/'+commit+'?recursive=1');(directory/'tree.json').write_bytes(tree)
    entries=json.loads(tree)['tree']
    if repo.startswith('armijn'):
        selected=[e['path'] for e in entries if e['type']=='blob' and ('qti' in e['path'].lower() or 'chromatix' in e['path'].lower())]
    else:
        selected=[e['path'] for e in entries if e['type']=='blob' and any(s in e['path'].lower() for s in ['parameterfile','parameterutils','sensormodule','sensordriver','sensor_library','chisensor','sensorinterface']) and e.get('size',0)<2_000_000]
    assert len(selected)<=60,(repo,len(selected))
    files=[]
    for name in selected:
        url=f'https://raw.githubusercontent.com/{repo}/{commit}/{name}';data=fetch(url)
        p=directory/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        files.append(dict(path=name,url=url,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data)))
    report=dict(repository='https://github.com/'+repo,commit=commit,files=files)
    (directory/'source-manifest.json').write_text(json.dumps(report,indent=2)+'\n');records.append(report)
(out/'parser-source-manifests.json').write_text(json.dumps(records,indent=2)+'\n')
print(json.dumps([dict(repository=r['repository'],commit=r['commit'],files=len(r['files']),paths=[x['path'] for x in r['files']]) for r in records],indent=2))
