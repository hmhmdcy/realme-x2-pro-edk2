"""Run the retained OEM entry function; OS/MMU providers are explicitly mocked."""
from pathlib import Path
import hashlib,json,struct
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_LR,UC_ARM_REG_PC,UC_ARM_REG_SP
import host
HERE=Path(__file__).resolve().parent;raw=(host.PRIVATE.parent/'kernel352/CAMERA_ICP.elf-private').read_bytes()
phoff=struct.unpack_from('<I',raw,28)[0];stride,count=struct.unpack_from('<HH',raw,42)
segments=[struct.unpack_from('<8I',raw,phoff+i*stride) for i in range(count)]
REG=0xe0010000;SHARED=0x07400000;HEAP=0x10a00000;ALLOC=0x05000000;STACK=0x02000000;STOP=0x04000000
cases=['success','no-shared-pointer','no-shared-size','no-heap-pointer','no-heap-size','heap-map-fails','register-isr-fails','create-signal-fails','create-mutex-fails','driver-thread-fails','sfr-map-fails','idle-thread-fails']
records=[]
for case in cases:
    u=Uc(UC_ARCH_ARM,UC_MODE_THUMB);maximum=(max(s[2]+s[5] for s in segments if s[0]==1)+4095)&~4095;u.mem_map(0,maximum)
    for kind,offset,va,pa,filesz,memsz,flags,align in segments:
        if kind==1:u.mem_write(va,raw[offset:offset+filesz])
    for addr,size in [(REG,4096),(0xe0044000,4096),(SHARED,0x20000),(HEAP,0x100000),(ALLOC,0x100000),(STACK,0x10000),(STOP,4096)]:u.mem_map(addr,size)
    registers={0x48:1,0x50:SHARED,0x54:0x09600000,0x5c:HEAP,0x60:0x100000,0x68:SHARED+0x1c000}
    for bad,key in [('no-shared-pointer',0x50),('no-shared-size',0x54),('no-heap-pointer',0x5c),('no-heap-size',0x60)]:
        if case==bad:registers[key]=0
    for offset,value in registers.items():u.mem_write(REG+offset,struct.pack('<I',value))
    u.mem_write(SHARED+0x1c000,struct.pack('<I',4096))
    state=dict(instructions=0,allocated=0,threads=0,maps=[],responses=[],provider_calls=[])
    def step(uc,pc,size,user):
        state['instructions']+=1
        if 0x24746<=pc<0x24c58:return
        r0=uc.reg_read(UC_ARM_REG_R0);r1=uc.reg_read(UC_ARM_REG_R1);r2=uc.reg_read(UC_ARM_REG_R2)
        result=0
        if pc==0x6cc0: # vSYS_AllocMem
            result=ALLOC+state['allocated'];state['allocated']+=(r0+15)&~15
            assert state['allocated']<0x100000
        elif pc==0x67bc: # vSYS_CreateThread: descriptors record idle/driver entry
            state['threads']+=1
            result=1 if (case=='idle-thread-fails' and state['threads']==1) or (case=='driver-thread-fails' and state['threads']==2) else 0
            if not result:uc.mem_write(r0,struct.pack('<I',state['threads']))
        elif pc in [0x6a58,0x6aa0,0x6e5a,0x742]:
            result=1 if (case=='register-isr-fails' and pc==0x6e5a) or (case=='create-signal-fails' and pc==0x6aa0) or (case=='create-mutex-fails' and pc==0x6a58 and state['threads']>0) else 0
            if not result:uc.mem_write(r0,struct.pack('<I',0x1234))
        elif pc==0x107ca:
            state['maps'].append(dict(address=r1,bytes=r2))
            result=1 if (case=='heap-map-fails' and r1==HEAP) or (case=='sfr-map-fails' and r1==SHARED+0x1c004) else 0
        elif pc==0x25ef4:uc.mem_write(r0,bytes([r1&255])*r2);result=r0 # memset
        elif pc in [0x7e1c,0x8316,0x1bf7e,0x6998,0x25b3e]:pass
        else:raise RuntimeError('Unexpected call outside entry function: '+hex(pc))
        state['provider_calls'].append(hex(pc));uc.reg_write(UC_ARM_REG_R0,result);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
    def write(uc,access,address,size,value,user):
        if address==REG+0x4c:state['responses'].append(value)
    u.hook_add(UC_HOOK_CODE,step);u.hook_add(UC_HOOK_MEM_WRITE,write)
    u.reg_write(UC_ARM_REG_SP,STACK+0xf000);u.reg_write(UC_ARM_REG_LR,STOP|1)
    u.emu_start(0x24747,STOP,timeout=1000000,count=20000)
    assert u.reg_read(UC_ARM_REG_PC)==STOP
    expected=[] if case=='idle-thread-fails' else [1] if case=='success' else [2]
    assert state['responses']==expected,(case,state)
    records.append(dict(case=case,expected_response=expected,actual_response=state['responses'],instructions=state['instructions'],mapping_requests=state['maps'],passed=True))
report=dict(stage=363,firmware_sha256=hashlib.sha256(raw).hexdigest(),actual_thumb_entry='fwEntryFunction',entry_start='0x24747',entry_bytes=1298,
    tests=records,initialization_success_value=1,initialization_failure_value=2,early_idle_thread_failure_leaves_response_zero=True,
    os_allocation_thread_signal_mutex_irq_and_mmu_calls_mocked=True,firmware_code_writes_hfi_csr=True,
    response_three_not_observed_on_exercised_paths=True,no_claim_about_other_firmware_paths=True,
    not_hardware_boot_or_actual_smmu_validation=True,phone_operations=False,passed=True)
(HERE/'firmware-init-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='tests'},indent=2))
