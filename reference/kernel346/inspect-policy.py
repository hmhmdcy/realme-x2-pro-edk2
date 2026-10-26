from pathlib import Path
import subprocess
import host
P=host.PRIVATE;source=P.parent/'kernel328/stats-source/com.qti.stats.aec.so'
for label,start,end in [('set-ev',0x294c0,0x29668),('set-fps',0x29ab8,0x29ba0),('set-table',0x29ba0,0x29e38)]:
 raw=subprocess.check_output(['aarch64-linux-gnu-objdump','-d','--start-address='+hex(start),'--stop-address='+hex(end),str(source)])
 (P/(label+'-private.asm')).write_bytes(raw)
print((P/'set-ev-private.asm').read_text())
