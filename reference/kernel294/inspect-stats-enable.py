"""Revisit only the pinned original HAL's register packing facts after zero-count hardware results."""
from pathlib import Path
import hashlib,subprocess
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel294');binary=PRIVATE.parent/'kernel281/camera.qcom.so-private'
assert hashlib.sha256(binary.read_bytes()).hexdigest()=='e2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde'
for label,a,b in [('stats-packing',0x2a8d90,0x2a8f28),('stats-pointers',0x2a9410,0x2a9508),('stats-writes',0x2a9980,0x2a99f0)]:
 p=PRIVATE/(label+'-disassembly-private.txt')
 data=subprocess.check_output(['aarch64-linux-gnu-objdump','-d',f'--start-address={a:#x}',f'--stop-address={b:#x}',str(binary)])
 p.write_bytes(data);print(data.decode())
