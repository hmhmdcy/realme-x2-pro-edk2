"""Recover only relevant symbols from the retained factory HAL mini debug ELF."""
from pathlib import Path
import hashlib,json,lzma,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;source=P.parent/'kernel281/camera.qcom.so-private';raw=source.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='e2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde'
off=struct.unpack_from('<Q',raw,40)[0];stride,count,strings=struct.unpack_from('<HHH',raw,58)
sections=[struct.unpack_from('<IIQQQQIIQQ',raw,off+i*stride) for i in range(count)];names=raw[sections[strings][4]:sections[strings][4]+sections[strings][5]]
debug=next(s for s in sections if names[s[0]:].split(b'\0')[0]==b'.gnu_debugdata')
path=P/'hal-debug-private.elf';path.write_bytes(lzma.decompress(raw[debug[4]:debug[4]+debug[5]]))
symbols=subprocess.check_output(['aarch64-linux-gnu-nm','-C','-n',str(path)],text=True)
(P/'hal-symbols-private.txt').write_text(symbols)
selected=[line for line in symbols.splitlines() if any(v in line for v in ['Gamma15','Gamma16','InverseGamma','IPENode::GetGamma','IPELTM13::CheckDependence','IPELTM13::UpdateIPEInternal','LTM13Setting::Calculate'])]
(P/'hal-gamma-symbols-private.txt').write_text('\n'.join(selected)+'\n')
print('\n'.join(selected))
