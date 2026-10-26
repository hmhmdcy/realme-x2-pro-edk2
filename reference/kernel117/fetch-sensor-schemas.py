from pathlib import Path
import urllib.request,json,hashlib,shutil,os
out=Path('/mnt/e/edk2-samurai-out/kernel117/CamxChi');m=json.loads((out/'source-manifest.json').read_text())
names=[n for n in (out/'tree-paths.txt').read_text().splitlines() if n.startswith('chi-cdk/api/sensor/') and n.endswith('.xsd')]
work=Path('/home/cy122/x2pro-linux/parser-k117');schema=work/'xsd';schema.mkdir(mode=0o700);os.chown(schema,1000,1000)
for name in names:
    p=out/name
    if not p.exists():
        url=f'https://raw.githubusercontent.com/bjzhou/CamxChi/{m["commit"]}/{name}'
        with urllib.request.urlopen(url,timeout=45) as r:data=r.read()
        p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        m['files'].append(dict(path=name,url=url,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data)))
    dest=schema/p.name;shutil.copyfile(p,dest);os.chown(dest,1000,1000)
source=out/'chi-cdk/api/chromatix/XSD/ParameterTuningTypes.xsd'
dest=schema/source.name;shutil.copyfile(source,dest);os.chown(dest,1000,1000)
(out/'source-manifest.json').write_text(json.dumps(m,indent=2)+'\n')
print('SENSOR_SCHEMA_SET_PRIVATE_STAGED',len(names))
