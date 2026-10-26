"""Pin platform selection and Demosaic36/CST12 interoperability facts."""
from pathlib import Path
import hashlib,json,struct
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parent
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel284')
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
        if base<=address and address+size<=base+length:
            return data[start+address-base:start+address-base+size]
    raise AssertionError(hex(address))
instructions={
    0x2c7a78:0x52953d09, 0x2c7a80:0x8b090014,
    0x2c7ac4:0x5280e0ab, 0x2c7ac8:0x72a0002b,
    0x2c7ad0:0x54000180, 0x2c7b0c:0xfd410d21, 0x2c7b14:0xfc004281,
    0x29302c:0x5294c003, 0x293038:0x8b0302b9,
    0x293408:0x3940228b, 0x29340c:0xb943ef2f, 0x293410:0x6a0b01ff,
    0x31a354:0x33160086, 0x37834c:0x12816271,
    0x378368:0x12009c91, 0x378378:0x121624e7,
    0x37838c:0x12002526, 0x3783b0:0x330c2d06,
    0x37b5b4:0x52a89010, 0x37b734:0x120032ba,
    0x37b738:0x120028c6, 0x37b73c:0x331032da,
    0x2a9008:0x910f227a, 0x2a98d0:0x52800981, 0x2a98dc:0xaa1a03e3,
    0x2a9070:0x910f127b, 0x2a98b8:0x52800901, 0x2a98c4:0xaa1b03e3,
    0x318a94:0x3300012b, 0x31f1c0:0x331d02a2,
    0x378274:0x2d420ae5, 0x378284:0x1e24004b,
    0x37835c:0x53081d6b, 0x378360:0x2a0a216a,
}
for address,value in instructions.items():assert struct.unpack('<I',read(address,4))[0]==value,hex(address)
mask,adjacent=struct.unpack('<II',read(0xd1218,8));assert (mask,adjacent)==(2,1920)
dem36=struct.unpack('<IIIIQ',read(0x5c0f58,24));dem37=struct.unpack('<IIIIQ',read(0x5c0f70,24))
assert dem36==(11,7,3,0,0x319b80) and dem37==(11,7,4,0,0x31a870)
assert mask&dem36[2] and not mask&dem37[2]
defaults=struct.unpack('<II',read(0xd21a0,8));assert defaults==(0x100,0x8000)
assert struct.unpack('<I',read(0x319fc4,4))[0]==0x52800cc2
assert struct.unpack('<I',read(0x319fcc,4))[0]==0x72a10002
schema=PRIVATE/'reference-demosaic_3_6_0.xsd-private'
root=ET.parse(schema).getroot();ns={'xs':'http://www.w3.org/2001/XMLSchema'}
layouts=[[e.get('name') for e in n.findall('./xs:sequence/xs:element',ns)] for n in root.findall('.//xs:complexType',ns)]
layout=next(fields for fields in layouts if 'lambda_g' in fields)
assert layout==['edge_det_weight','edge_det_noise_offset','dis_directional_g','dis_directional_rb',
                'lambda_g','lambda_rb','en_dyna_clamp_g','en_dyna_clamp_rb'],layout
report=dict(stage=284,hal_sha256=sha,static_only=True,selected_demosaic='Demosaic36',
            platform_mask=mask,descriptor_masks={'Demosaic36':dem36[2],'Demosaic37':dem37[2]},
            selection_trace='Titan175 0x10705 -> root+0xa9ec mask2 -> descriptor +8 AND mask -> Demosaic36 Create',
            adjacent_1920_word_not_used_as_line_width=True,
            demosaic_registers={'config':'0x6f8','interpolation':'0x71c','classifier':'0x720','enable':'0x40 bit10'},
            demosaic_fields={'config_owned_mask':'0xb13','lambda_g':'15:8','lambda_rb':'31:24',
                              'classifier_w':'9:0 signed','classifier_a':'31:20; matching algorithm bounds0..400'},
            demosaic_initial_profile={'config':'0x100','interpolation':'0x8000','classifier':'0x08000066'},
            profile_is_uncalibrated_bringup_default=True,
            cst_facts={'base':'0xf30','words':12,'coefficient':'signed13 Q10','offset_fields':'11 bits',
                       'clamp_fields':'10 bits','enable':'0x4c bit0','implementation_pending':True},
            cst_enable_pointer_trace='calc+968 at0x2a9008 -> x26 -> write0x4c at0x2a98d0-0x2a98e0',
            gamma_enable_pointer_trace='calc+964 at0x2a9070 -> x27 -> write0x48 at0x2a98b8-0x2a98c8; Gamma sets bit3',
            demosaic_schema_order=layout,demosaic_schema_sha256=hashlib.sha256(schema.read_bytes()).hexdigest(),
            checked_instruction_addresses=[hex(a) for a in instructions],
            external_layout_references=json.loads((PRIVATE/'reference-layout-sources-private.json').read_text()),
            external_sources_only_crosschecks=True,original_implementation_not_copied=True,
            private_binary_and_reference_text_not_published=True,not_hardware_validated=True)
(ROOT/'oem-pixel-contract-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='external_layout_references'},indent=2))
