from pathlib import Path
import json,re,subprocess,urllib.request
import host
ROOT=Path(__file__).resolve().parent;TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
rows={}
for p in (TREE/'drivers/media/platform/qcom/camss').glob('*.c'):
 hits=[(i+1,l) for i,l in enumerate(p.read_text().splitlines()) if re.search('BHIST|bhist|vfe_add_stats',l)]
 if hits:rows[p.name]=hits
print(json.dumps(rows,indent=2))
repo=Path('/mnt/e/Realme X2 Pro移植主线Linux/sources/realme-downstream.git');commit='9668fcdc6ec15be7a10d66f7b93c347829e0fdb6'
paths=subprocess.check_output(['git','-C',str(repo),'ls-tree','-r','--name-only',commit,'drivers/media/platform/msm/camera'],text=True).splitlines()
print('OEM paths',json.dumps([p for p in paths if re.search('bls|bhist|vfe175',p,re.I)],indent=2))
url='https://api.github.com/repos/bjzhou/CamxChi/git/trees/9f17f1b568626b393e785b369c5dc94543774d7a?recursive=1'
target=host.PRIVATE/'camx-reference-tree-private.json'
if not target.exists():target.write_bytes(urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Samurai-camera-interoperability'}),timeout=30).read())
tree=json.loads(target.read_bytes());assert not tree.get('truncated')
paths=[p['path'] for p in tree['tree'] if p['type']=='blob' and re.search('bls12|bhist.*17|titan170ife',p['path'],re.I)]
(ROOT/'reference-paths.json').write_text(json.dumps(dict(stage=294,camx_commit='9f17f1b568626b393e785b369c5dc94543774d7a',paths=paths),indent=2)+'\n')
print('Camx reference paths',json.dumps(paths,indent=2))
