from pathlib import Path
import urllib.request,hashlib,json,subprocess
out=Path('/mnt/e/edk2-samurai-out/kernel117/CamxChi');m=json.loads((out/'source-manifest.json').read_text())
names=['chi-cdk/api/sensor/camxsensorcommon.xsd','chi-cdk/api/sensor/camxmoduleconfig.xsd','chi-cdk/api/chromatix/XSD/ParameterTuningTypes.xsd','chi-cdk/tools/buildbins/linux64/ParameterParser']
for name in names:
    p=out/name;assert not p.exists()
    url=f'https://raw.githubusercontent.com/bjzhou/CamxChi/{m["commit"]}/{name}'
    with urllib.request.urlopen(url,timeout=45) as r:data=r.read(3_000_001)
    assert len(data)<=3_000_000
    p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    m['files'].append(dict(path=name,url=url,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data)))
(out/'source-manifest.json').write_text(json.dumps(m,indent=2)+'\n')
p=out/names[-1]
kind=subprocess.check_output(['file',str(p)],text=True)
strings=subprocess.check_output(['strings','-a',str(p)],text=True)
(out/'parameter-parser-strings-private.txt').write_text(strings)
print(kind)
print('\n'.join(l for l in strings.splitlines() if any(s in l.lower() for s in ['usage','command','binaryparameter','binaryfile','decrypt','deserialize','decompile','parsebinary','output','unpack']))[:6800])
