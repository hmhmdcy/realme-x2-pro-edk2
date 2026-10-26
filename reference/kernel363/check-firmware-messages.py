"""Execute OEM SYS_INIT/PING handling against explicit synthetic register data."""
from pathlib import Path
import json,struct
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_LR,UC_ARM_REG_PC,UC_ARM_REG_SP
import host
HERE=Path(__file__).resolve().parent;raw=(host.PRIVATE.parent/'kernel352/CAMERA_ICP.elf-private').read_bytes()
phoff=struct.unpack_from('<I',raw,28)[0];stride,count=struct.unpack_from('<HH',raw,42)
segments=[struct.unpack_from('<8I',raw,phoff+i*stride) for i in range(count)]
STACK=0x02000000;STOP=0x04000000;DATA=0x05000000;CMD=DATA+0x1000;HOST=DATA+0x2000;CHIP=DATA+0x3000
records=[]
for command,cookie in [(0x10001,0),(0x10005,0),(0x10005,0x0123456789abcdef),(0x10005,0xffffffffffffffff)]:
    u=Uc(UC_ARCH_ARM,UC_MODE_THUMB);maximum=(max(s[2]+s[5] for s in segments if s[0]==1)+4095)&~4095;u.mem_map(0,maximum)
    for kind,offset,va,pa,filesz,memsz,flags,align in segments:
        if kind==1:u.mem_write(va,raw[offset:offset+filesz])
    for addr,size in [(STACK,0x10000),(STOP,4096),(DATA,0x10000),(0xe0000000,0x100000)]:u.mem_map(addr,size)
    u.mem_write(0x120938,struct.pack('<I',CHIP));u.mem_write(CHIP,struct.pack('<9I',2,0,1,0,0,0,0,0,8))
    packet=struct.pack('<IIQ',16,command,cookie);u.mem_write(CMD,packet)
    state=dict(instructions=0,replies=[])
    def step(uc,pc,size,user):
        state['instructions']+=1
        if 0x1aa38<=pc<0x1b734:return
        if pc==0x1ba40:
            pointer=uc.reg_read(UC_ARM_REG_R1);length=struct.unpack('<I',uc.mem_read(pointer,4))[0]
            assert 8<=length<=256;state['replies'].append(bytes(uc.mem_read(pointer,length)))
        elif pc in [0x7e1c,0x8316]:pass
        else:raise RuntimeError('Unexpected provider call: '+hex(pc))
        uc.reg_write(UC_ARM_REG_R0,0);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
    u.hook_add(UC_HOOK_CODE,step);u.reg_write(UC_ARM_REG_SP,STACK+0xf000);u.reg_write(UC_ARM_REG_LR,STOP|1)
    u.reg_write(UC_ARM_REG_R0,HOST);u.reg_write(UC_ARM_REG_R1,CMD);u.reg_write(UC_ARM_REG_R2,command)
    u.emu_start(0x1aa39,STOP,timeout=1000000,count=20000)
    assert u.reg_read(UC_ARM_REG_PC)==STOP and len(state['replies'])==1
    reply=state['replies'][0];length,kind=struct.unpack_from('<II',reply)
    if command==0x10001:assert length==56 and kind==0x20001 and struct.unpack_from('<I',reply,8)[0]==0
    else:assert length==16 and kind==0x20006 and struct.unpack_from('<Q',reply,8)[0]==cookie
    records.append(dict(command=hex(command),reply_type=hex(kind),reply_bytes=length,cookie_exact=command==0x10005,instructions=state['instructions'],passed=True))
report=dict(stage=363,actual_thumb_function='ICPDomainCmdHandler',tests=records,sys_init_reply_bytes=56,ping_reply_bytes=16,
    sys_init_error_offset=8,ping_cookie_u64_offset=8,host_post_message_and_logging_mocked=True,synthetic_chip_and_mmio_data=True,
    initialization_and_scheduler_not_executed=True,no_phone_operations=True,passed=True)
(HERE/'firmware-messages-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
