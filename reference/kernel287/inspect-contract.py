"""Inspect bounded Demux/MNDS/IPP contracts from saved, fixed source material."""
from pathlib import Path
import hashlib,json,struct,subprocess

ROOT=Path(__file__).resolve().parent
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel287');PRIVATE.mkdir(mode=0o700,exist_ok=True)
HAL=Path('/mnt/e/edk2-samurai-out/kernel281/camera.qcom.so-private')
data=HAL.read_bytes()
assert hashlib.sha256(data).hexdigest()=='e2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde'
for name,start,end in [('demux-calculate',0x377d90,0x378204),('mnds-update',0x32bb48,0x32bbe4),('mnds-resolution',0x32e458,0x32e738)]:
    path=PRIVATE/(name+'-disassembly-private.txt')
    if not path.exists():
        result=subprocess.run(['aarch64-linux-gnu-objdump','-d',f'--start-address={hex(start)}',f'--stop-address={hex(end)}',str(HAL)],check=True,text=True,capture_output=True)
        path.write_text(result.stdout)
print(json.dumps(dict(stage=287,hal_sha256=hashlib.sha256(data).hexdigest(),static_only=True,
                     input_normalization_not_assumed=True,not_deployed=True)))
