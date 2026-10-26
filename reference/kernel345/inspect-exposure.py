from pathlib import Path
import subprocess
import host
P=host.PRIVATE;source=P.parent/'kernel328/stats-source/com.qti.stats.aec.so'
for label,start,end in [('lookup',0x2d9a0,0x2dbd8),('set-table',0x29ba0,0x29e38),('active-knees',0x2d508,0x2d9a0),('fps-knee',0x2d178,0x2d350),('ev-knee',0x2d350,0x2d508)]:
 raw=subprocess.check_output(['aarch64-linux-gnu-objdump','-d','--start-address='+hex(start),'--stop-address='+hex(end),str(source)])
 (P/(label+'-private.asm')).write_bytes(raw)
print((P/'lookup-private.asm').read_text())
