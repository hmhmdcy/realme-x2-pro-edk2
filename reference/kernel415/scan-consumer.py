"""Locate original TMC10/11 consumers from exact binary diagnostic strings."""
import json,struct,subprocess
import host
P=host.PRIVATE;hal=P.parent/'kernel281/camera.qcom.so-private';raw=hal.read_bytes()
markers=[b'IPE LTM : using TMC 1.0',b'IPE LTM : using TMC 1.1',b'IFE GTM : using TMC 1.0',b'IFE GTM : using TMC 1.1']
addresses={}
for marker in markers:
    at=raw.index(marker);addresses[raw.rfind(b'\0',0,at)+1]=marker.decode()
found={v:[] for v in addresses.values()}
phoff=struct.unpack_from('<Q',raw,32)[0];stride,count=struct.unpack_from('<HH',raw,54)
for i in range(count):
    kind,flags,off,va,pa,length,mem,align=struct.unpack_from('<II6Q',raw,phoff+i*stride)
    if kind!=1 or not flags&1:continue
    for pos in range(0,length-36,4):
        word=struct.unpack_from('<I',raw,off+pos)[0]
        if word&0x9f000000!=0x90000000:continue
        imm=((word>>5)&0x7ffff)<<2|((word>>29)&3)
        if imm&(1<<20):imm-=1<<21
        page=((va+pos)&~4095)+(imm<<12);rd=word&31
        if not any(page==a&~4095 for a in addresses):continue
        for delta in range(4,36,4):
            add=struct.unpack_from('<I',raw,off+pos+delta)[0]
            if add&0xff000000==0x91000000 and (add>>5)&31==rd and not add&(1<<22):
                address=page+((add>>10)&4095)
                if address in addresses:found[addresses[address]].append(va+pos)
(P/'consumer-refs-private.json').write_text(json.dumps(found,indent=2)+'\n')
for values in found.values():
    for at in values:
        raw=subprocess.check_output(['aarch64-linux-gnu-objdump','-d','--start-address='+hex(at-1800),'--stop-address='+hex(at+500),str(hal)])
        (P/('consumer-'+hex(at)+'-private.asm')).write_bytes(raw)
print({k:[hex(a) for a in v] for k,v in found.items()})
