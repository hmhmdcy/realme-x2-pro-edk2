"""Bind bank trace to the maintained RT handle and native target bit packing."""
from pathlib import Path
import importlib.util,json,re
from unicorn.arm64_const import UC_ARM64_REG_W3,UC_ARM64_REG_W8,UC_ARM64_REG_W11,UC_ARM64_REG_PC
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
k=module('storage431banks',HERE.parent/'kernel284/storage.py').mounted_build().parent/'source354'
h=(k/'drivers/media/platform/qcom/camss/camss-icp-a5-boot.h').read_text();adapter=(k/'drivers/media/platform/qcom/camss/camss-icp-a5-m2m.c').read_text()
assert re.search(r'CAMSS_A5_IPE_RT\s*(?:=|\s)\s*2',h)
assert 'camss_a5_ipe_create(dev->a5, &ctx->session, CAMSS_A5_IPE_RT)' in adapter
native=module('ltm431',HERE.parent/'kernel403/ltm-model.py').LTM();u=native.u
for bank in [0,1]:
 u.reg_write(UC_ARM64_REG_W11,0);u.reg_write(UC_ARM64_REG_W3,bank)
 u.emu_start(0x365884,0x365888,count=1);assert u.reg_read(UC_ARM64_REG_PC)==0x365888 and u.reg_read(UC_ARM64_REG_W11)==bank<<14
 u.reg_write(UC_ARM64_REG_W8,bank);u.emu_start(0x3658a4,0x3658a8,count=1)
 assert u.reg_read(UC_ARM64_REG_W11)==(bank<<14)|(bank<<15)
report=json.loads((HERE/'bank-validation.json').read_text())
report.update(current_maintained_m2m_rt_type2_verified=True,target_hal_native_bank_bit_insertion_executed=True,target_hal_dc_bank_bit=14,target_hal_ip_bank_bit=15,
 initialization_scope='DC sum-clear at first coarse pass; IP retains same-bank result. Full SRAM contents not exported.',
 synchronization_scope='Original firmware final pass distribution/BL retained; same-request DC then IP. Cold/warm causal validation reused430; no custom bank override.',passed=True)
(HERE/'bank-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
