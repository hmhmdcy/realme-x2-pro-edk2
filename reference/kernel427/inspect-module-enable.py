"""Inspect the original IFE module-enable aggregation, beyond data registers."""
from pathlib import Path
import hashlib,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
blob=P.parent/'kernel281/camera.qcom.so-private'
assert hashlib.sha256(blob.read_bytes()).hexdigest()=='e2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde'
symbols=(P.parent/'kernel281/hal-debug-symbols-with-size-private.txt').read_text();rows=[]
for name in ['IFENode::ProgramIQModuleEnableConfig','IFENode::ProgramIQEnable','IFERoundClamp11::UpdateIFEInternalData','IFEPreCrop10::UpdateIFEInternalData']:
 matches=[l for l in symbols.splitlines() if name+'(' in l]
 if not matches:continue
 fields=matches[0].split(maxsplit=3);start,size=int(fields[0],16),int(fields[1],16)
 raw=subprocess.check_output(['aarch64-linux-gnu-objdump','-d','--start-address='+hex(start),'--stop-address='+hex(start+size),str(blob)])
 (P/(name.replace('::','-')+'-private.asm')).write_bytes(raw);rows.append(dict(name=name,address=hex(start),bytes=size))
(HERE/'module-enable-functions.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows))
