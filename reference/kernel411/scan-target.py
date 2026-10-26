"""Locate retained math calls and save bounded private disassembly windows."""
import json,struct,subprocess
import host
P=host.PRIVATE;hal=P.parent/'kernel281/camera.qcom.so-private';raw=hal.read_bytes()
off=struct.unpack_from('<Q',raw,32)[0];stride,count=struct.unpack_from('<HH',raw,54)
targets={0x5b1320:'log',0x5b12c0:'logf',0x5b1960:'powf',0x3c6328:'sample'};found={v:[] for v in targets.values()}
for i in range(count):
    kind,flags,start,va,pa,n,mem,align=struct.unpack_from('<II6Q',raw,off+i*stride)
    if kind!=1 or not flags&1:continue
    for pos in range(0,n-3,4):
        word=struct.unpack_from('<I',raw,start+pos)[0]
        if word>>26!=0b100101:continue
        imm=word&0x3ffffff;imm=imm-(1<<26) if imm&(1<<25) else imm
        target=va+pos+imm*4
        if target in targets:found[targets[target]].append(va+pos)
(P/'math-call-sites-private.json').write_text(json.dumps(found,indent=2)+'\n')
print({k:[hex(a) for a in v] for k,v in found.items() if k!='powf'})
for address in found['log']:
    result=subprocess.check_output(['aarch64-linux-gnu-objdump','-d','--start-address='+hex(max(0,address-700)),'--stop-address='+hex(address+1300),str(hal)])
    (P/('log-near-'+hex(address)+'-private.asm')).write_bytes(result)
print('log windows retained',len(found['log']))
