from pathlib import Path
import hashlib,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;out=P/'sources';out.mkdir(exist_ok=True)
repo='/home/cy122/x2pro-linux/refs/CamxChi-k117';commit='9f17f1b568626b393e785b369c5dc94543774d7a'
paths=['camx/src/hwl/ispiqmodule/camxipeica10.cpp','camx/src/hwl/ispiqmodule/camxipeupscaler12.cpp','camx/src/hwl/iqsetting/icasetting.cpp','camx/src/hwl/iqsetting/icautils.cpp']
rows=[]
for path in paths:
 target=out/Path(path).name
 if not target.exists():target.write_bytes(subprocess.check_output(['git','-C',repo,'show',commit+':'+path],timeout=55))
 rows.append(dict(path=path,bytes=target.stat().st_size,sha256=hashlib.sha256(target.read_bytes()).hexdigest()))
(HERE/'reference-sources.json').write_text(json.dumps(dict(stage=382,repo_commit=commit,files=rows),indent=2)+'\n')
# Use this device's retained HAL assembly as the ABI authority.
raw=P.parent/'kernel281/camera.qcom.so-private'
for name,start,end in [('hal-ica-execute',0x359b78,0x35d900),('hal-upscaler12',0x372af8,0x373c20)]:
 q=subprocess.run(['aarch64-linux-gnu-objdump','-d','-C','--start-address='+hex(start),'--stop-address='+hex(end),str(raw)],capture_output=True,check=True)
 (P/(name+'-private.asm')).write_bytes(q.stdout)
print(json.dumps(dict(stage=382,files=len(rows),target_hal_sections_retained=True)))
