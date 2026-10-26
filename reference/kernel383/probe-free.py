from pathlib import Path
import importlib.util
from unicorn.arm_const import *
from unicorn import UC_HOOK_MEM_READ,UC_HOOK_MEM_READ_AFTER
spec=importlib.util.spec_from_file_location('fm',Path(__file__).resolve().parent/'firmware-model.py');f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
for kind in [None,UC_HOOK_MEM_READ,'bounded']:
 m=f.Machine()
 if kind=='bounded':m.u.hook_add(UC_HOOK_MEM_READ,lambda *args:None,begin=f.DATA+0x30000,end=f.DATA+0x31000)
 elif kind:m.u.hook_add(kind,lambda *args:None)
 m.call(0xf21e,f.DATA,phase='free-empty')
 print('hook',kind,'SP',hex(m.u.reg_read(UC_ARM_REG_SP)),'trace',m.free_trace,'CPSR',hex(m.u.reg_read(UC_ARM_REG_CPSR)))
