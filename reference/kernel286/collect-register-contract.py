"""Collect fixed sources and bounded disassembly privately for the 175 backends."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,subprocess,urllib.request

ROOT=Path(__file__).resolve().parent
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel286');PRIVATE.mkdir(mode=0o700,exist_ok=True)
OEM_COMMIT='9668fcdc6ec15be7a10d66f7b93c347829e0fdb6'
REF_COMMIT='9f17f1b568626b393e785b369c5dc94543774d7a'
requests=[('realme-kernel-opensource/realmeX2Pro-kernel-source',OEM_COMMIT,'drivers/media/platform/msm/camera/cam_cdm/'+n) for n in
          ['cam_cdm_virtual.c','cam_cdm_util.c','cam_cdm_util.h','cam_cdm_hw_reg.h']]
requests += [('bjzhou/CamxChi',REF_COMMIT,n) for n in
             ['camx/src/core/camxpacketbuilder.cpp','camx/src/csl/camxcdmdefs.cpp','camx/src/csl/camxcdmdefs.h',
              'camx/src/hwl/isphwsetting/pipeline/ife/camxtitan170ife.h']]
def fetch(item):
    repo,commit,name=item;url=f'https://raw.githubusercontent.com/{repo}/{commit}/{name}'
    target=PRIVATE/('reference-'+Path(name).name+'-private')
    try:
        if target.exists():data=target.read_bytes()
        else:
            data=urllib.request.urlopen(url,timeout=30).read();target.write_bytes(data)
        return dict(url=url,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),path=name)
    except Exception as e:return dict(url=url,path=name,error=str(e))
with ThreadPoolExecutor(max_workers=4) as pool:sources=list(pool.map(fetch,requests))
(PRIVATE/'register-reference-sources-private.json').write_text(json.dumps(sources,indent=2)+'\n')
hal=Path('/mnt/e/edk2-samurai-out/kernel281/camera.qcom.so-private')
assert hashlib.sha256(hal.read_bytes()).hexdigest()=='e2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde'
for name,start,end in [('write-dmi',0x52d2e8,0x52d6e4),('gamma-calculate',0x37b9d0,0x37c814)]:
    path=PRIVATE/(name+'-disassembly-private.txt')
    if not path.exists():
        p=subprocess.run(['aarch64-linux-gnu-objdump','-d',f'--start-address={hex(start)}',f'--stop-address={hex(end)}',str(hal)],check=True,text=True,capture_output=True)
        path.write_text(p.stdout)
print(json.dumps(sources,indent=2))
