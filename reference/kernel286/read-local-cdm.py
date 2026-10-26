"""Read the pinned official GPL camera sources from the existing bare clone."""
from pathlib import Path
import hashlib,json,subprocess,urllib.request

ROOT=Path(__file__).resolve().parent
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel286')
REPO=Path('/mnt/e/Realme X2 Pro移植主线Linux/sources/realme-downstream.git')
COMMIT='9668fcdc6ec15be7a10d66f7b93c347829e0fdb6'
sources={}
for name in ['cam_cdm.h','cam_cdm_virtual.h','cam_cdm_virtual_core.c','cam_hw_cdm170_reg.h']:
    path='drivers/media/platform/msm/camera/cam_cdm/'+name
    data=subprocess.check_output(['git','--git-dir='+str(REPO),'show',COMMIT+':'+path])
    (PRIVATE/('reference-'+name+'-private')).write_bytes(data)
    sources[path]=dict(commit=COMMIT,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),read_from_existing_git=True)
(PRIVATE/'local-cdm-sources-private.json').write_text(json.dumps(sources,indent=2)+'\n')
# A bounded retry for the missing cross-check; keep the first network failures.
results=[]
for name in ['camx/src/core/camxpacketbuilder.cpp','camx/src/csl/camxcdmdefs.cpp','camx/src/csl/camxcdmdefs.h']:
    target=PRIVATE/('reference-'+Path(name).name+'-private')
    url='https://raw.githubusercontent.com/bjzhou/CamxChi/9f17f1b568626b393e785b369c5dc94543774d7a/'+name
    try:
        if target.exists():data=target.read_bytes()
        else:data=urllib.request.urlopen(url,timeout=8).read();target.write_bytes(data)
        results.append(dict(url=url,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data)))
    except Exception as e:results.append(dict(url=url,error=str(e)))
(PRIVATE/'cdm-retry-sources-private.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(dict(official_files=sources,references=results),indent=2))
