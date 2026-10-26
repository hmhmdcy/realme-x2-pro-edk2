from pathlib import Path
import hashlib
import json

out=Path('/mnt/e/edk2-samurai-out/kernel73')
names=('boot-before.img','logdump-before.img','boot-k73-display.img',
       'logdump-k73-display.img','logdump-k73-display-deps.img',
       'Image-before','Image-display','Image-display-deps','config-before','config-display-deps')
files={name:dict(bytes=(out/name).stat().st_size,
    sha256=hashlib.sha256((out/name).read_bytes()).hexdigest()) for name in names}
assert files['boot-k73-display.img']['sha256']=='57508887131ae55cf9465fa1a44280fa45b507a3439345ffe635dc7544eaa999'
assert files['logdump-k73-display-deps.img']['sha256']=='c7778d45c336b35cf75c2842c083b513343f59a0a1864fe52ad2105d3d55e6c7'
result=dict(local_directory=str(out),artifacts=files,
    deployed_pair=['boot-k73-display.img','logdump-k73-display-deps.img'],
    rollback_pair=['boot-before.img','logdump-before.img'])
Path(__file__).with_name('artifact-manifest.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
