"""Verify bounded VFE175 interoperability facts from the private original HAL."""
from pathlib import Path
import hashlib
import json
import struct

ROOT = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel283')
OEM = Path('/mnt/e/edk2-samurai-out/kernel281')
binary = (OEM/'camera.qcom.so-private').read_bytes()
sha = hashlib.sha256(binary).hexdigest()
assert sha == 'e2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde'
offset = struct.unpack_from('<Q',binary,32)[0]
size,count = struct.unpack_from('<HH',binary,54)
loads=[]
for i in range(count):
    kind,flags,fileoff,vaddr,physical,filesize,memsize,align = struct.unpack_from('<IIQQQQQQ',binary,offset+i*size)
    if kind == 1:
        loads.append((vaddr,fileoff,filesize))

def read(vaddr,size):
    for base,start,length in loads:
        if base <= vaddr and vaddr+size <= base+length:
            return binary[start+vaddr-base:start+vaddr-base+size]
    raise AssertionError(hex(vaddr))

labels={0x5f638:'G_Gain',0x8bdcb:'B_Gain',0xb7cdd:'R_Gain'}
for address,label in labels.items():
    assert label.encode() in read(address,80).split(b'\0',1)[0]
text=(OEM/'IFEWB12-Execute-disassembly-private.txt').read_text()
expected={
    '335814':'ldr\tw1, [x20, #76]',
    '335834':'and\tw5, w1, #0xfff',
    '335884':'ldrh\tw8, [x20, #78]',
    '3358a4':'and\tw5, w8, #0xfff',
    '3358f4':'ldr\tw10, [x20, #80]',
    '335914':'and\tw5, w10, #0xfff',
    '335a80':'add\tx3, x20, #0x4c',
    '335a84':'mov\tw1, #0x6fc',
    '335a88':'mov\tw2, #0x4',
    '3356cc':'mov\tw4, #0x43000000',
    '335ab0':'mov\tw4, #0x3c000000',
}
for address,instruction in expected.items():
    lines=[line for line in text.splitlines() if line.strip().startswith(address+':')]
    assert len(lines)==1 and instruction in lines[0], (address,instruction)
gain_reserved = struct.unpack('<Q',read(0xd2478,8))[0]
offset_reserved = struct.unpack('<Q',read(0xd13c0,8))[0]
assert gain_reserved == 0xfffff000f000f000
assert offset_reserved == 0xffff800080008000
records=json.loads((PRIVATE/'posted-sources-private.json').read_text())
modules=(PRIVATE/'modules-posted-private.txt').read_text()
assert 'U15Q10' in modules and 'GENMASK(30, 16)' in modules
report=dict(stage=283,hal_sha256=sha,static_only=True,
            channel_mapping={'0x6fc[11:0]':'green','0x6fc[27:16]':'blue','0x700[11:0]':'red'},
            gain_format='unsigned 12-bit Q7',unity=128,
            parameter_format='existing common U15Q10, rounded and saturated to hardware Q7',
            gain_reserved_mask_64=hex(gain_reserved),offset_reserved_mask_64=hex(offset_reserved),
            instruction_addresses=list(expected),label_addresses=[hex(a) for a in labels],
            disassembly_sha256=hashlib.sha256(text.encode()).hexdigest(),
            original_implementation_not_copied=True,private_binary_not_published=True,
            offset_semantics_not_inferred_from_masks=True,nonzero_offsets_not_supported=True,
            other_platform_rejected='SM8250 v10x module offsets and U15Q10 hardware gains differ; no wholesale port',
            posted_sources=records,not_hardware_validated=True)
(ROOT/'oem-wb-contract-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='posted_sources'},indent=2))
