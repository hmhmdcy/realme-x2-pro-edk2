from pathlib import Path
import subprocess,json,hashlib,urllib.request
out=Path('/mnt/e/edk2-samurai-out/kernel117')
assert out.exists() and not (out/'parser-source-manifests.json').exists()
def fetch(url):
    request=urllib.request.Request(url,headers={'User-Agent':'samurai-camera-research'})
    with urllib.request.urlopen(request,timeout=45) as r:return r.read()
records=[]
for repo,branch in [('armijnhemel/binaryanalysis-ng','master'),('bjzhou/CamxChi','main')]:
    directory=out/repo.split('/')[-1];directory.mkdir(exist_ok=True)
    checkout=Path('/home/cy122/x2pro-linux/refs')/(repo.split('/')[-1]+'-k117')
    assert not checkout.exists()
    with (directory/'git-fetch-private.log').open('wb') as log:
        subprocess.run(['git','clone','--depth','1','--filter=blob:none','--no-checkout','--branch',branch,'https://github.com/'+repo+'.git',str(checkout)],stdout=log,stderr=log,timeout=90,check=True)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=checkout,text=True).strip()
    entries=subprocess.check_output(['git','ls-tree','-r','--name-only','HEAD'],cwd=checkout,text=True).splitlines()
    (directory/'tree-paths.txt').write_text('\n'.join(entries)+'\n')
    if repo.startswith('armijn'):
        selected=[name for name in entries if 'qti' in name.lower() or 'chromatix' in name.lower()]
    else:
        selected=[name for name in entries if any(s in name.lower() for s in ['parameterfile','parameterutils','sensormodule','sensordriver','sensor_library','chisensor','sensorinterface']) and name.endswith(('.h','.cpp','.c','.xsd','.xml'))]
    assert len(selected)<=60,(repo,len(selected))
    files=[]
    for name in selected:
        url=f'https://raw.githubusercontent.com/{repo}/{commit}/{name}';data=fetch(url)
        assert len(data)<3_000_000
        p=directory/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        files.append(dict(path=name,url=url,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data)))
    report=dict(repository='https://github.com/'+repo,commit=commit,files=files,git_checkout=str(checkout),github_api_rate_limited=True)
    (directory/'source-manifest.json').write_text(json.dumps(report,indent=2)+'\n');records.append(report)
    print(json.dumps(dict(repository=repo,commit=commit,files=len(files)),indent=2),flush=True)
(out/'parser-source-manifests.json').write_text(json.dumps(records,indent=2)+'\n')
