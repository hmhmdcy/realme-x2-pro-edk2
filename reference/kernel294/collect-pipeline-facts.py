from pathlib import Path
import hashlib,json,re,urllib.request
import host
tree=json.loads((host.PRIVATE/'camx-reference-tree-private.json').read_bytes());commit='9f17f1b568626b393e785b369c5dc94543774d7a'
paths=[p['path'] for p in tree['tree'] if p['type']=='blob' and re.search(r'(camxtitan170ife\.cpp|camxispiqmodule\.h|camxispstatsmodule\.h|camxifeproperty\.h)$',p['path'])]
rows=[]
for path in paths:
 p=host.PRIVATE/('reference-'+Path(path).name+'-private');url=f'https://raw.githubusercontent.com/bjzhou/CamxChi/{commit}/{path}'
 if not p.exists():p.write_bytes(urllib.request.urlopen(url,timeout=25).read())
 rows.append(dict(path=path,url=url,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size))
 lines=p.read_text().splitlines();selected=set()
 for i,l in enumerate(lines):
  if re.search('Bhist|BHIST|bhist|BHist|BlackLevel',l):selected.update(range(max(0,i-3),min(len(lines),i+5)))
 print(p.name+'\n'+'\n'.join(f'{i+1}: {lines[i]}' for i in sorted(selected)))
(Path(__file__).resolve().parent/'pipeline-source-facts.json').write_text(json.dumps(dict(stage=294,sources=rows),indent=2)+'\n')
