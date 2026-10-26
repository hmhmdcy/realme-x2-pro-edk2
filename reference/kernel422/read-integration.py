from pathlib import Path
import importlib.util,json,shutil
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py')
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s);base=s.mounted_build().parent
tree=base/'libcamera421-frame-history/src/libcamera-v0.7.2'
directory=tree/'src/libcamera/pipeline/camss-vfe'
print('PIPELINE FILES',[p.name for p in directory.iterdir() if p.suffix in ['.h','.cpp']])
copies=Path('/mnt/e/edk2-samurai-out/kernel422/integration-source');copies.mkdir(exist_ok=True)
for path in [tree/'src/ipa/camss-vfe/camss.cpp',tree/'include/libcamera/ipa/camss.mojom',*directory.glob('*.cpp'),*directory.glob('*.h')]:
    shutil.copyfile(path,copies/path.name)
for path in [tree/'src/ipa/camss-vfe/camss.cpp',*directory.glob('*ipe*')]:
    text=path.read_text();lines=text.splitlines();print('SOURCE',path.name)
    matches=[i for i,l in enumerate(lines) if any(k in l for k in ['ipeParameters','IpeParameters','prepareIpe','ipeLtm','IpeLtm','prepareParameters(', 'buildParameters(', 'bypass', 'Bypass', 'LTM', 'struct Parameters'])]
    seen=set()
    for i in matches:
        for j in range(max(0,i-3),min(len(lines),i+20)):
            if j not in seen: print(str(j+1)+':'+lines[j]);seen.add(j)
roots=json.loads(Path('/mnt/e/edk2-samurai-out/kernel351/sunny_imx471-ltm13_ipe-trees-private.json').read_text())
root=roots[0];print('LTM rootkeys',list(root));print('reservekeys',list(root['reserve']))
def shape(v):
    if isinstance(v,dict):return {k:shape(w) for k,w in v.items()}
    if isinstance(v,list):return ['length='+str(len(v)),shape(v[0]) if v else None]
    return type(v).__name__
print('LTM shape',json.dumps(shape(root)))
gamma=json.loads(Path('/mnt/e/edk2-samurai-out/kernel350/mode-profiles-private.json').read_text())
for name,value in gamma.items():
    print('GAMMA SELECTED SHAPE',name,json.dumps(shape(value))[:2500])
    break
