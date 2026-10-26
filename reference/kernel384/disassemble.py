from pathlib import Path
import subprocess
P=Path('/mnt/e/edk2-samurai-out/kernel384')
for name,start,end in [('module1d',0x146ec0,0x146ff0),('isp-config',0x146ff0,0x148000),('ltm-stripe',0x1556a0,0x155a00)]:
 raw=subprocess.check_output(['aarch64-linux-gnu-objdump','-d','--start-address='+hex(start),'--stop-address='+hex(end),str(P.parent/'kernel281/camera.qcom.so-private')],text=True)
 (P/(name+'-private.asm')).write_text(raw)
print('Retained bounded original HAL disassembly privately.')
