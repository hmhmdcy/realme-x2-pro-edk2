"""Link the real HAL's module/command output to the firmware enable register."""
from pathlib import Path
import importlib.util,json,struct
from unicorn.arm64_const import UC_ARM64_REG_X19,UC_ARM64_REG_X20,UC_ARM64_REG_PC
from unicorn.arm_const import UC_ARM_REG_R9,UC_ARM_REG_R5,UC_ARM_REG_PC as FW_PC
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
c=module('colour396',HERE/'colour-model.py');f=module('fw383',HERE.parent/'kernel383/firmware-model.py')
hal=c.Colour();D=c.DATA;registers=hal.calculate([1.,0,0,0,1.,0,0,0,1.],[0,0,0],0);expected=hal.command(registers);rows=[]
for enabled in [0,1]:
 obj=D+0xc000;data=D+0xd000;array=D+0xe000;iq=D+0xf000
 for addr,n in [(obj,1024),(data,4096),(array,128),(iq,2584)]:hal.u.mem_write(addr,bytes(n))
 hal.u.mem_write(obj+12,struct.pack('<I',enabled));hal.u.mem_write(obj+152,registers)
 hal.u.mem_write(data+2584,struct.pack('<Q',iq));hal.u.mem_write(data+2600,struct.pack('<Q',array));hal.u.mem_write(array+32,struct.pack('<Q',D+0xa000));hal.u.mem_write(D+0xb000,bytes([0xa7])*64)
 hal.u.reg_write(UC_ARM64_REG_X19,obj);hal.u.reg_write(UC_ARM64_REG_X20,data)
 hal.u.emu_start(0x350b18,0x350b5c,timeout=1000000,count=1000);assert hal.u.reg_read(UC_ARM64_REG_PC)==0x350b5c
 assert hal.read32(iq+2188)==enabled
 assert bytes(hal.u.mem_read(D+0xb000,44))==(expected if enabled else bytes([0xa7])*44)
 rows.append(dict(enabled=bool(enabled),iq_offset=2188,command_buffer_index=4,packet_emitted=bool(enabled),command_range=0x5e68,passed=True))
fwrows=[]
for value in [0,1,2,3,0xffffffff]:
 machine=f.Machine();u=machine.u;u.mem_write(f.DATA,bytes(2584));u.mem_write(f.DATA+2188,struct.pack('<I',value));u.mem_write(f.DATA+0x10000,bytes([0xa7])*64)
 u.reg_write(UC_ARM_REG_R9,f.DATA);u.reg_write(UC_ARM_REG_R5,f.DATA+0x10000)
 u.emu_start(0x114d5,0x114e4,timeout=1000000,count=20);assert u.reg_read(FW_PC)==0x114e4
 reg,actual=struct.unpack('<2I',u.mem_read(f.DATA+0x10000+16,8));assert reg==0x5e60 and actual==value&1
 fwrows.append(dict(iq_value=value,register=reg,register_value=actual,passed=True))
report=dict(stage=396,hal_cases=rows,firmware_cases=fwrows,hal_module_fragment=['0x350b18','0x350b5c'],firmware_iq_to_register_fragment=['0x114d4','0x114e4'],original_full_hal_packet_encoder_called_from_module_fragment=True,original_full_hal_execute_and_firmware_full_frame_handler_not_claimed=True,hardware_execution=False,phone_changed=False,passed=True)
(HERE/'enable-abi-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
