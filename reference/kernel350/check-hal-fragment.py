"""Check the retained factory HAL's normal Gamma15 numerical LUT loop."""
from pathlib import Path
import json,struct,sys
import host
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'kernel329'))
from stock_emulator import StockMath,OBJECT,STACK,TLS,STOP,OUT
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_INTR
from unicorn.arm64_const import UC_ARM64_REG_CPACR_EL1,UC_ARM64_REG_TPIDR_EL0,UC_ARM64_REG_SP,UC_ARM64_REG_X9,UC_ARM64_REG_X15,UC_ARM64_REG_X23
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
class GammaFragment(StockMath):
 def __init__(self,source):
  self.uc=Uc(UC_ARCH_ARM64,UC_MODE_ARM);self.begin=0x355148;self.end=0x35528c
  self.calls=0;self.instructions=0;self.stub_calls=0
  raw=source.read_bytes();off=struct.unpack_from('<Q',raw,32)[0];stride,count=struct.unpack_from('<HH',raw,54)
  segments=[struct.unpack_from('<IIQQQQQQ',raw,off+i*stride) for i in range(count)]
  maximum=max(s[3]+s[6] for s in segments if s[0]==1);maximum=(maximum+4095)&~4095;assert maximum<OBJECT
  self.uc.mem_map(0,maximum)
  for kind,flags,offset,va,pa,filesz,memsz,align in segments:
   if kind==1:self.uc.mem_write(va,raw[offset:offset+filesz])
  for address,length in [(OBJECT,0x100000),(STACK,0x10000),(TLS,0x1000),(STOP,0x3000),(OUT,0x1000)]:self.uc.mem_map(address,length)
  self.uc.reg_write(UC_ARM64_REG_CPACR_EL1,3<<20);self.uc.reg_write(UC_ARM64_REG_TPIDR_EL0,TLS)
  self.uc.hook_add(UC_HOOK_CODE,self._step);self.uc.hook_add(UC_HOOK_INTR,self._interrupt)
 def evaluate(self,samples):
  # Original runtime channel data is an enum32 followed by257 float samples.
  self.uc.mem_write(OBJECT,struct.pack('<I257f',0,*samples));self.uc.mem_write(OUT,b'\0'*1024)
  self.uc.reg_write(UC_ARM64_REG_SP,STACK+0xe000);self.uc.reg_write(UC_ARM64_REG_X9,OBJECT)
  self.uc.reg_write(UC_ARM64_REG_X15,0);self.uc.reg_write(UC_ARM64_REG_X23,OUT)
  self.uc.emu_start(self.begin,self.end,timeout=2000000,count=20000)
  from unicorn.arm64_const import UC_ARM64_REG_PC
  assert self.uc.reg_read(UC_ARM64_REG_PC)==self.end
  self.calls+=1;return bytes(self.uc.mem_read(OUT,1024))
def main():
 source=P.parent/'kernel281/camera.qcom.so-private';engine=GammaFragment(source)
 raw=(P/'oracle-input-private.bin').read_bytes();expected=(P/'oracle-output-private.bin').read_bytes();assert len(raw)%1028==0
 actual=b''.join(engine.evaluate(struct.unpack_from('<257f',raw,i)) for i in range(0,len(raw),1028))
 (P/'hal-actual-private.bin').write_bytes(actual);assert actual==expected
 report=dict(stage=350,source_evidence='../kernel286/register-contract-validation.json',source_file_retained_from281=True,
  original_hal_normal_gamma15_math_fragment=['0x355148','0x35528c'],caller_register_setup_controlled=True,
  curves=engine.calls,compared_bytes=len(actual),differing_bytes=0,instructions=engine.instructions,
  android_loader_not_used=True,hardware_not_accessed=True,system_calls_rejected=True,
  no_math_or_logging_stub_calls=engine.stub_calls==0,
  does_not_verify_full_hal_module_enable_contrast_hdr_or_processing_graph=True,phone_changed=False,passed=True)
 (HERE/'hal-fragment-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
