"""Recheck bounded CST12 facts from the actual saved OEM HAL; do not execute it."""
from pathlib import Path
import hashlib,json,struct

ROOT=Path(__file__).resolve().parent
OEM=Path('/mnt/e/edk2-samurai-out/kernel281')
data=(OEM/'camera.qcom.so-private').read_bytes()
sha=hashlib.sha256(data).hexdigest()
assert sha=='e2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde'
off=struct.unpack_from('<Q',data,32)[0];size,count=struct.unpack_from('<HH',data,54)
loads=[]
for i in range(count):
    kind,flags,start,vaddr,physical,length,memsize,align=struct.unpack_from('<IIQQQQQQ',data,off+i*size)
    if kind==1:loads.append((vaddr,start,length))
def read(address,size):
    for base,start,length in loads:
        if base<=address and address+size<=base+length:return data[start+address-base:start+address-base+size]
    raise AssertionError(hex(address))
instructions={
    0x318954:0x5281e601,0x318958:0x52800182, # base0xf30, twelve words
    0x318a90:0xb943c82b,0x318a94:0x3300012b, # calc+968 bit0
    0x2a9008:0x910f227a,0x2a98d0:0x52800981,0x2a98dc:0xaa1a03e3, # pointer ->0x4c
    0x37b5b4:0x52a89010, # float1024 before coefficient quantization
    0x37b734:0x120032ba,0x37b73c:0x331032da, # signed13 low/upper
    0x37b738:0x120028c6,0x37b740:0x33102ae6, # eleven-bit offsets
    0x37b76c:0x120696da, # preserve clamp's non-owned bits
}
for address,value in instructions.items():assert struct.unpack('<I',read(address,4))[0]==value,hex(address)
# The Execute fallback loads three literal vectors into the 12-word command.
words=[]
for address in [0xd10f0,0xd04d0,0xd0b80]:words+=list(struct.unpack('<4I',read(address,16)))
assert words==[0x00750259,0x132,0,0x03ff0000,0x01fe1eae,0x1f54,0x02000000,0x03ff0000,
               0x1fad1e55,0x1fe,0x02000000,0x03ff0000],[hex(w) for w in words]
def s13(n):return (n&8191)-8192 if n&4096 else n&8191
decoded=[[s13(words[i*4]),s13(words[i*4]>>16),s13(words[i*4+1])] for i in range(3)]
assert decoded==[[601,117,306],[-338,510,-172],[-427,-83,510]]
report=dict(stage=285,hal_sha256=sha,static_only=True,cst_base='0xf30',words=12,enable='0x4c bit0',
            signed_coefficient_bits=13,fraction_bits=10,offset_bits=11,clamp_bits=10,
            checked_instruction_addresses=[hex(a) for a in instructions],
            original_default_coefficient_slots=decoded,
            gbr_slot_order_inferred_from_stock_bt601_profile=True,hardware_slot_order_test_pending=True,
            output_offset_used_input_offset_zero=True,standard_matrices_derived_independently=True,
            no_oem_implementation_copied=True,no_binary_execution=True,no_hardware_writes=True,
            prior_public_ife_series='https://lists.openwall.net/linux-kernel/2026/10/07/534',
            matrix_equations='https://www.kernel.org/doc/html/latest/userspace-api/media/v4l/colorspaces-details.html',
            existing_ope_parameters_not_reinterpreted_as_cst=True)
(ROOT/'cst-oem-contract-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
