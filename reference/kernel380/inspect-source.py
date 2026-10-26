from pathlib import Path
import hashlib,importlib.util,json,subprocess
HERE=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel380');P.mkdir(mode=0o700,exist_ok=True)
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
assert git('rev-parse','HEAD')=='6b8e3b1a28ff9ea60391045b03b746499d1d9400' and not git('status','--porcelain')
elf=P.parent/'kernel352/CAMERA_ICP.elf-private';hal=P.parent/'kernel281/camera.qcom.so-private'
assert hashlib.sha256(hal.read_bytes()).hexdigest()=='e2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde'
for name,a,b in [('striping-create',0x144348,0x144a78),('striping-wrapper',0x144a78,0x146ec0),('hal-frame-buffer',0x2e3a00,0x2e3eb8),('hal-process-request',0x2cf408,0x2e17d0),('hal-plt',0x5b1000,0x5b4000)]:
 q=subprocess.run(['aarch64-linux-gnu-objdump','-d','--start-address='+hex(a),'--stop-address='+hex(b),str(hal)],capture_output=True,check=True);(P/(name+'-private.asm')).write_bytes(q.stdout)
for name,a,b in [('frame-handler',0x17f30,0x19b00),('frame-callback',0x1eaf2,0x1ec0c)]:
 q=subprocess.run(['arm-linux-gnueabi-objdump','-d','-m','armv7','--start-address='+hex(a),'--stop-address='+hex(b),str(elf)],capture_output=True,check=True);(P/(name+'-private.asm')).write_bytes(q.stdout)
(HERE/'source-before.json').write_text(json.dumps(dict(stage=380,source=str(source),commit=git('rev-parse','HEAD'),branch=git('branch','--show-current'),clean=True,phone_mutated=False),indent=2)+'\n')
print('Verified source379; retained bounded original striping, frame and callback instruction windows privately.')
