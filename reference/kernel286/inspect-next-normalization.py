"""Acquire pinned Demux/MNDS layout cross-checks without copying OEM implementation."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,subprocess,urllib.request

ROOT=Path(__file__).resolve().parent
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel286')
paths=['camx/src/hwl/iqsetting/demux13setting.cpp','camx/src/hwl/iqsetting/demux13setting.h',
       'camx/src/hwl/isphwsetting/titan17x/camxifedemux13titan17x.cpp',
       'camx/src/hwl/isphwsetting/titan17x/camxifedemux13titan17x.h',
       'camx/src/hwl/isphwsetting/titan17x/camxifemnds16titan17x.cpp',
       'camx/src/hwl/isphwsetting/titan17x/camxifemnds16titan17x.h']
def fetch(path):
    url='https://raw.githubusercontent.com/bjzhou/CamxChi/9f17f1b568626b393e785b369c5dc94543774d7a/'+path
    target=PRIVATE/('reference-'+Path(path).name+'-private')
    try:
        if target.exists():data=target.read_bytes()
        else:data=urllib.request.urlopen(url,timeout=12).read();target.write_bytes(data)
        return dict(url=url,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))
    except Exception as e:return dict(url=url,error=str(e))
with ThreadPoolExecutor(max_workers=3) as pool:sources=list(pool.map(fetch,paths))
(PRIVATE/'next-normalization-sources-private.json').write_text(json.dumps(sources,indent=2)+'\n')
hal=Path('/mnt/e/edk2-samurai-out/kernel281/camera.qcom.so-private')
for name,start,end in [('mnds16-execute',0x329ea0,0x32a028),('mnds16-calculation',0x32a528,0x32bb44)]:
    target=PRIVATE/(name+'-disassembly-private.txt')
    if not target.exists():
        p=subprocess.run(['aarch64-linux-gnu-objdump','-d',f'--start-address={hex(start)}',f'--stop-address={hex(end)}',str(hal)],check=True,text=True,capture_output=True)
        target.write_text(p.stdout)
print(json.dumps(dict(files=sources,demux_mnds_not_implemented=True),indent=2))
