from pathlib import Path
import io, json, re, struct, wave
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel104';out=Path('/mnt/e/edk2-samurai-out/kernel104')
ns={};exec((ref/'verify-tests.py').read_text().split('runtime=archive(',1)[0],ns)
for n in range(3):
    f=ns['archive'](f'capture-dmic{n}.tar',f'k104-capture-dmic{n}')
    with wave.open(io.BytesIO(f['mic-private.wav'])) as w:
        count=w.getnframes();values=struct.unpack('<'+'h'*count,w.readframes(count))
    print(json.dumps(dict(dmic=n,frames=count,exit=f['capture-exit.txt'].decode().strip(),nonzero_samples=sum(v!=0 for v in values),minimum=min(values,default=0),maximum=max(values,default=0),distinct=len(set(values)))))
    for l in f['dapm-live.txt'].decode().splitlines():
        if re.match(r'^(DMIC[012]|MIC BIAS[13]|MCLK):',l):print(l)
    for l in f['dmesg.txt'].decode().splitlines():
        if 'samurai slim trigger' in l:print(l)
    print('capture stderr:',f['capture-error.txt'].decode())
