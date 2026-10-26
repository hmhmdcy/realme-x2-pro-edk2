from pathlib import Path
import bisect,re,subprocess
import host
P=host.PRIVATE;source=P.parent/'kernel328/stats-source/com.qti.stats.aec.so'
text=subprocess.check_output(['aarch64-linux-gnu-objdump','-d',str(source)],text=True)
symbols=[]
for line in (P.parent/'kernel336/aec-symbols-private.txt').read_text().splitlines():
 match=re.match(r'([0-9a-f]+) [tT] (.*)',line)
 if match:symbols.append((int(match[1],16),match[2]))
addresses=[row[0] for row in symbols];rows=[]
for line in text.splitlines():
 if re.search(r'\bbl\s+294c0\b',line):
  address=int(line.split(':',1)[0],16);start,name=symbols[bisect.bisect_right(addresses,address)-1]
  end=addresses[bisect.bisect_right(addresses,address)]
  raw=subprocess.check_output(['aarch64-linux-gnu-objdump','-d','--start-address='+hex(start),'--stop-address='+hex(end),str(source)])
  (P/('ev-caller-'+hex(address)+'-private.asm')).write_bytes(raw);rows.append(dict(call=hex(address),function=name,start=hex(start),end=hex(end)))
import json
(P/'ev-policy-callers-private.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))
