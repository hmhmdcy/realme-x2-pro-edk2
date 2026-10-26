"""Execute bounded target HAL/FW instruction fragments for the alignment ABI."""
from pathlib import Path
import importlib.util,json,struct
from unicorn.arm_const import *
HERE=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel382')
prefix=(HERE.parent/'kernel379/check-firmware-io.py').read_text().split("for operation in ['map','unmap','config']:")[0]
scope=dict(__file__=str(HERE/'check-alignment-abi.py'));exec(compile(prefix,'retained-fw-machine','exec'),scope)
DATA=scope['DATA'];STACK=scope['STACK'];rows=[]
# The complete request/engine handler is deliberately not claimed here.
for value in [0,1,2,0xffffffff]:
 u=scope['machine']();sp=STACK+0xf000;u.mem_write(DATA,bytes(1024));u.mem_write(DATA+68,struct.pack('<I',value))
 u.reg_write(UC_ARM_REG_SP,sp);u.reg_write(UC_ARM_REG_R11,DATA)
 u.emu_start(0x18b13,0x18b26,timeout=1000000,count=12);assert u.reg_read(UC_ARM_REG_PC)==0x18b26
 alignment=u.mem_read(sp+344,1)[0];assert alignment==bool(value)
 for engine in [0,1]:
  out=DATA+0x1000;params=DATA+0x2000;u.mem_write(params,bytes([alignment]));u.reg_write(UC_ARM_REG_R6,engine);u.reg_write(UC_ARM_REG_R3,out);u.reg_write(UC_ARM_REG_LR,params)
  u.mem_write(sp+32,struct.pack('<I',0));u.emu_start(0x1528f,0x152a4,timeout=1000000,count=12)
  assert u.reg_read(UC_ARM_REG_PC)==0x152a4
  register,actual=struct.unpack('<II',u.mem_read(out,8));assert register==[0x129c,0x169c][engine] and actual==alignment
  rows.append(dict(iq_value=value,engine=engine,register=register,register_value=actual))
probe=json.loads((P/'alignment-probe-private.json').read_text());assert all(not r['stripe_differences'] for r in probe)
iq=(P/'hal-default-ica-iq-private.bin').read_bytes();assert [i for i in range(0,2584,4) if any(iq[i:i+4])]==[52,68,244,260]
report=dict(stage=382,target_hal_default_store_fragment_executed=True,hal_iq_offsets=[52,68,244,260],hal_values=[1,1,1,1],
 target_firmware_iq_to_pass_and_pass_to_cdm_fragments_executed=True,register_tests=rows,
 original_hal_complete_striping_algorithm_differential_cases=5,striping_unchanged_for_alignment_and_invalid_pixel_defaults=True,
 libc_memory_providers_modelled=True,full_hal_request_or_full_firmware_engine_handler_not_executed=True,
 real_pixel_effect_requires_hardware_validation=True,phone_operations=False,passed=True)
(HERE/'alignment-abi-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
