"""Locate bounded direct target TMC calls for private version-policy analysis."""
import json,struct,subprocess
import host
P=host.PRIVATE;hal=P.parent/'kernel281/camera.qcom.so-private';raw=hal.read_bytes()
phoff=struct.unpack_from('<Q',raw,32)[0];stride,count=struct.unpack_from('<HH',raw,54)
targets={0x3774b0:'tmc10_interpolation',0x3c7070:'pchip_sampler',0x3c7580:'bezier_sampler',0x3c7c98:'contrast_sampler'}
found={name:[] for name in targets.values()}
for i in range(count):
    kind,flags,start,va,pa,n,mem,align=struct.unpack_from('<II6Q',raw,phoff+i*stride)
    if kind!=1 or not flags&1:continue
    for pos in range(0,n-3,4):
        word=struct.unpack_from('<I',raw,start+pos)[0]
        if word>>26!=0b100101:continue
        imm=word&0x3ffffff;imm=imm-(1<<26) if imm&(1<<25) else imm;address=va+pos
        target=address+imm*4
        if target in targets:found[targets[target]].append(address)
print({k:[hex(v) for v in vs] for k,vs in found.items()})
(P/'tmc-direct-call-sites-private.json').write_text(json.dumps(found,indent=2)+'\n')
for values in found.values():
    for address in values:
        (P/('call-near-'+hex(address)+'-private.asm')).write_bytes(subprocess.check_output(['aarch64-linux-gnu-objdump','-d',
            '--start-address='+hex(address-220),'--stop-address='+hex(address+160),str(hal)]))
