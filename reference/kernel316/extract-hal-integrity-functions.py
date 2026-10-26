from pathlib import Path
import json,re,struct,subprocess
import host
P=host.PRIVATE;path=P/'hal-source/camera.qcom.so';raw=path.read_bytes()
frames=subprocess.check_output(['aarch64-linux-gnu-readelf','--debug-dump=frames',str(path)],text=True)
ranges=[tuple(int(x,16) for x in m) for m in re.findall(r'FDE .*?pc=([0-9a-f]+)\.\.([0-9a-f]+)',frames)]
for address in [0x504648,0x504b18,0x504f30,0x505cc8,0x505f18]:
 a,b=next((a,b) for a,b in ranges if a<=address<b)
 text=subprocess.check_output(['aarch64-linux-gnu-objdump','-d','--start-address='+hex(a),'--stop-address='+hex(b),str(path)],text=True)
 (P/('hal-helper-'+hex(a)+'.txt')).write_text(text)
 print('function',hex(a),hex(b),'bytes',b-a)
for address in [0x87c2a,0xa15b4,0xa15c3,0x4fa75,0x94b92,0xc7666,0x8e812]:
 print(hex(address),raw[address:].split(b'\0',1)[0][:200].decode(errors='replace'))
