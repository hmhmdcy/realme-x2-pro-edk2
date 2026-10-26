from pathlib import Path
import re,json,tarfile
out=Path('/mnt/e/edk2-samurai-out/kernel119/gpu-coredump')
lines=(out/'decoded-summary-private.txt').read_text(errors='replace').splitlines()
for i,line in enumerate(lines):
    if 'ESTIMATED CRASH LOCATION' in line:
        print('LOCATION_CONTEXT_PACKET_AND_REGISTER_NAMES')
        for j in range(max(0,i-18),min(len(lines),i+24)):
            # Only publish opcode/register tokens, never raw command buffers.
            names=re.findall(r'\b(?:CP|RB|SP|TPL1|GRAS|PC|VFD|VPC|HLSQ|UCHE|CCU)_[A-Z0-9_]+\b',lines[j])
            if names:print(j,','.join(dict.fromkeys(names)))
        print('estimated_location_line',i)
print('WARN_ERROR_CATEGORIES')
for line in lines:
    if any(s in line.lower() for s in ['error:','unknown packet','invalid packet','could not','couldn\'t','not captured']):
        clean=re.sub(r'0x[0-9a-fA-F]+|\b[0-9a-fA-F]{8,}\b','[private-value]',line)
        if len(clean)<400:print(clean)
print('CORE_TOP_LEVEL_KEYS')
core=(out/'devcd2-private.data').read_text(errors='replace')
print(re.findall(r'^([a-zA-Z][a-zA-Z0-9_-]*):',core,re.M)[:60])
print('FAULT_AND_BO_SECTION_SHAPE')
raw=core.splitlines()
for key in ['fault-info:','pgtable-fault-info:','bos:']:
    i=next(i for i,line in enumerate(raw) if line==key)
    print(key)
    for line in raw[i+1:i+16]:
        if line and not line[0].isspace():break
        print(re.sub(r'0x[0-9a-fA-F]+|\b[0-9a-fA-F]{8,}\b','[private-value]',line))
