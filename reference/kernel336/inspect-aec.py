"""Inspect only the retained AEC algorithm and its embedded symbol table."""
from pathlib import Path
import json,lzma,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
path=P.parent/'kernel328/stats-source/com.qti.stats.aec.so';raw=path.read_bytes()
shoff=struct.unpack_from('<Q',raw,40)[0];stride,count,strings=struct.unpack_from('<HHH',raw,58)
sections=[struct.unpack_from('<IIQQQQIIQQ',raw,shoff+i*stride) for i in range(count)]
names=raw[sections[strings][4]:sections[strings][4]+sections[strings][5]]
debug=next(s for s in sections if names[s[0]:].split(b'\0')[0]==b'.gnu_debugdata')
data=lzma.decompress(raw[debug[4]:debug[4]+debug[5]]);out=P/'aec-debug-private.elf';out.write_bytes(data)
symbols=subprocess.check_output(['aarch64-linux-gnu-nm','-C','-n',str(out)],text=True)
(P/'aec-symbols-private.txt').write_text(symbols)
selected=[line for line in symbols.splitlines() if any(word in line.lower() for word in ['lux','sensitivity','exposureindex','exposure_index','calibrat'])]
(P/'aec-selected-symbols-private.txt').write_text('\n'.join(selected)+'\n')
print('\n'.join(selected))
