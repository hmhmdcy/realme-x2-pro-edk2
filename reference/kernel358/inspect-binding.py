"""Trace anti-banding tuning ownership through the retained native call sites."""
from pathlib import Path
import hashlib, json, struct, sys, xml.etree.ElementTree as ET

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'kernel329'))
from stock_emulator import StockMath,OBJECT,STACK,STOP
from unicorn.arm64_const import UC_ARM64_REG_PC,UC_ARM64_REG_LR,UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2,UC_ARM64_REG_SP

HERE=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel358')
path=P.parent/'kernel328/stats-source/com.qti.stats.aec.so';raw=path.read_bytes()
phoff=struct.unpack_from('<Q',raw,32)[0];stride,count=struct.unpack_from('<HH',raw,54)
segments=[struct.unpack_from('<II6Q',raw,phoff+i*stride) for i in range(count)]
def offset(va):
    s=next(s for s in segments if s[0]==1 and s[3]<=va<s[3]+s[5]);return s[2]+va-s[3]
def word(va):return struct.unpack_from('<I',raw,offset(va))[0]

pattern=struct.pack('<3Q',0x1def8,0x1df00,0x1df08);at=raw.index(pattern)
segment=next(s for s in segments if s[0]==1 and s[2]<=at<s[2]+s[5]);vtable=segment[3]+at-segment[2]
assert struct.unpack_from('<Q',raw,at+160)[0]==0x1dfc8
shoff=struct.unpack_from('<Q',raw,40)[0];stride,count=struct.unpack_from('<HH',raw,58);relr=set()
for i in range(count):
    section=struct.unpack_from('<IIQQQQIIQQ',raw,shoff+i*stride)
    if section[1] not in [19,0x6fffff00]:continue
    where=0
    for pos in range(section[4],section[4]+section[5],8):
        value=struct.unpack_from('<Q',raw,pos)[0]
        if not value&1:relr.add(value);where=value+8
        else:
            relr.update(where+(bit-1)*8 for bit in range(1,64) if value&(1<<bit));where+=63*8
assert vtable+160 in relr
instructions={
    0x23bc4:0xf9405169, # virtual getArbTuning slot160
    0x23c28:0xf9002540, # its pointer stored at module+72
    0x2409c:0x91010298, # CArbitrator at module+64
    0x2a510:0xf94006cb, # CArbitrator+8 -> tuning pointer holder
    0x2a528:0xb9408148, # tuning+128 -> FPS method
    0x2a600:0xf9401d50, # tuning+56 -> min preview blanking
    0x29cb0:0x91004295, # CExpTable at CArbitrator+16
    0x2d55c:0xbd401945, # selected source table+24 -> fraction
    0x2d57c:0xbd002365, # CExpTable+32 = CArbitrator+48
    0x2a4f8:0xbd4032c5, # same fraction read by anti-banding
}
for address,expected in instructions.items():assert word(address)==expected,hex(address)

ns={'x':'http://www.w3.org/2001/XMLSchema'}
schema=P.parent/'kernel336/sources/aecglobalelements.xsd'
root=ET.parse(schema).getroot()
enum=root.find('x:simpleType[@name="AECAntibandingVsFPSMethod"]',ns)
values=[e.attrib['value'] for e in enum.findall('.//x:enumeration',ns)]
assert values==['LegacyAllowFPSToDrop','StrictlyEnforceFPS','MaximizeExposureTime']

class HeaderCopy(StockMath):
    def __init__(self):super().__init__(path,0x2d508,0x2d584)
    def _step(self,uc,pc,size,user):
        if pc==0x58720:
            dest,source,length=[uc.reg_read(r) for r in [UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2]]
            uc.mem_write(dest,bytes(uc.mem_read(source,length)));uc.reg_write(UC_ARM64_REG_X0,dest)
            uc.reg_write(UC_ARM64_REG_PC,uc.reg_read(UC_ARM64_REG_LR));self.stub_calls+=1;return
        super()._step(uc,pc,size,user)
    def copy(self,fraction):
        self.write(OBJECT,'<Q',OBJECT+0x1000)
        self.write(OBJECT+24,'<Q',OBJECT+0x3000)
        self.write(OBJECT+32,'<f',-123.)
        self.write(OBJECT+0x1000,'<fI8xQf',1.,2,OBJECT+0x2000,fraction)
        self.uc.mem_write(OBJECT+0x2000,bytes(range(48)))
        self.uc.reg_write(UC_ARM64_REG_X0,OBJECT);self.uc.reg_write(UC_ARM64_REG_SP,STACK+0xf000)
        self.uc.reg_write(UC_ARM64_REG_LR,STOP)
        self.uc.emu_start(self.begin,self.end,timeout=2000000,count=2000)
        assert self.uc.reg_read(UC_ARM64_REG_PC)==self.end
        assert self.read(OBJECT+32,'<I')[0]==struct.unpack('<I',struct.pack('<f',fraction))[0]
        assert bytes(self.uc.mem_read(OBJECT+0x3000,48))==bytes(range(48))

policies=json.loads((P/'policies-private.json').read_text())
fractions={struct.pack('<f',p['threshold']) for p in policies}
copy=HeaderCopy()
for fraction in fractions:copy.copy(struct.unpack('<f',fraction)[0])
report=dict(stage=358,source_sha256=hashlib.sha256(raw).hexdigest(),arbitration_getter_virtual_offset=160,
    arbitration_getter_address='0x1dfc8',getter_slot_covered_by_relr=True,
    tuning_pointer_from_named_arbitration_getter=True,arbitrator_module_offset=64,
    fps_method_tuning_offset=128,minimum_preview_blanking_tuning_offset=56,
    threshold_selected_table_offset=24,threshold_arbitrator_offset=48,
    selected_table_fraction_copy_original_fragment=['0x2d508','0x2d584'],
    different_factory_fractions_copied=len(fractions),copy_only_memcpy_stub=True,
    fps_policy_enum_names=values,retained_schema_sha256=hashlib.sha256(schema.read_bytes()).hexdigest(),
    original_runtime_struct_header_not_available=True,field_names_cross_checked_with_retained_compatible_schema=True,
    actual_android_runtime_values_not_observed=True,passed=True)
(HERE/'tuning-binding-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
