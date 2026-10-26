"""Recheck actual HAL bytes and official CDM transport facts without executing OEM code."""
from pathlib import Path
import hashlib,json,re,struct

ROOT=Path(__file__).resolve().parent
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel286')
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
    0x33277c:0xfd400501,0x332780:0x0f003581, # calc+972+8: full Y/C enable0xc00
    0x3329b4:0x52a1fe09,0x332890:0x52a7fe09, # max255/1023 in29:20
    0x3329f4:0x72b801f7,0x332a00:0x121d0870,0x332a04:0x121a64f1,
    0x332a20:0x321f05c0,0x332a28:0x32000982, # roundY pattern3+2bits, C interleaved1
    0x2a91b8:0x910f5270,0x2a91bc:0xf81c83b0, # calc980 pointer -> stack-56
    0x2a9228:0x910f6262,0x2a922c:0xf81c03a2, # calc984 ->stack-64
    0x2a9914:0xf85c83a3,0x2a991c:0x5281c181, # ->fullYenable0xe0c
    0x2a992c:0xf85c03a3,0x2a9934:0x5281c581, # ->fullCenable0xe2c
    0x333918:0x5281c717,0x33391c:0x5281c301, # Y0xe18/C0xe38 pair
    0x31f68c:0x5280f301,0x31f6c4:0x52818498,0x31f6dc:0x52802005, # LUTcfg,DMIcfg,256bytes
    0x31f72c:0x52800340,0x31f734:0x52800384,0x31f73c:0x528003c3, # G26 B28 R30
    0x31f1c0:0x331d02a2,0x2a9070:0x910f127b,0x2a98b8:0x52800901,0x2a98c4:0xaa1b03e3,
    0x37c788:0x33000109,0x37c798:0x331f010a,0x37c7a8:0x331e010b, # bankbits0,1,2
    0x37c644:0x52803fec,0x37c648:0x12803fee,0x37c75c:0x53162470, # slope511/-512 & shift10
}
for address,value in instructions.items():assert struct.unpack('<I',read(address,4))[0]==value,hex(address)
assert 0x333910+read(0xd38d6,1)[0]*4==0x333910
cdm=PRIVATE/'reference-cam_cdm_util.c-private';text=cdm.read_text()
assert hashlib.sha256(cdm.read_bytes()).hexdigest()=='a8e7b34834a20eff561427477828fccdf534cdaa78057283392ffa3f722a7942'
assert re.search(r'#define CAM_CDM_DMI_DATA_HI_OFFSET\s+8',text)
assert re.search(r'#define CAM_CDM_DMI_DATA_LO_OFFSET\s+12',text)
assert 'swd_dmi->DMIAddr + CAM_CDM_DMI_DATA_LO_OFFSET' in text
report=dict(stage=286,hal_sha256=sha,static_only=True,
            round=dict(y_enable='0xe0c bits10/11',c_enable='0xe2c bits10/11',y_pair=['0xe18','0xe1c'],c_pair=['0xe38','0xe3c'],
                       clamp_min='9:0',clamp_max='29:20',round_bits='5:3',pattern='2:1',interleaved='0',
                       nv12_output_bits=8,output_clamp_max=255,not_cst_clamp_layout=True),
            gamma=dict(entries=64,reference_points=65,base_bits='9:0',signed_delta_bits='19:10',terminal_knot_max=1024,
                       lut_cfg='0x798 bits0..2',enable='0x48 bit3',dmi_cfg='0xc24',dmi_addr='0xc28',dmi_data_lo='0xc30',
                       selectors_rgb_bank0=[30,26,28],dmi_data_hi_not_used=True,explicit_address_per_entry=True,
                       auto_increment_not_assumed=True,dmi_selector_width_from_u8_cdm_contract=8,
                       register_port_behavior_and_physical_channel_bank_order_pending_hardware=True,
                       not_reusing_ope_256_u8_curves=True),
            checked_instruction_addresses=[hex(a) for a in instructions],
            official_cdm_source=dict(commit='9668fcdc6ec15be7a10d66f7b93c347829e0fdb6',sha256=hashlib.sha256(cdm.read_bytes()).hexdigest(),
                                    path='drivers/media/platform/msm/camera/cam_cdm/cam_cdm_util.c'),
            source_network_initial_failures_retained=True,local_official_git_fallback_used=True,
            no_oem_binary_execution=True,no_oem_implementation_copied=True,not_hardware_validated=True)
(ROOT/'register-contract-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
