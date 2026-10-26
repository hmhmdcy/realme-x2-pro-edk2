"""Recover the factory LTM flags from original defaults and constructor reads."""
from pathlib import Path
import importlib.util,json,struct
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('fragment350',HERE.parent/'kernel350/check-hal-fragment.py');fragment=importlib.util.module_from_spec(spec);spec.loader.exec_module(fragment)
from unicorn.arm64_const import *
OBJECT,STACK,STOP=fragment.OBJECT,fragment.STACK,fragment.STOP
READ=STOP+0x1000;STORE=OBJECT+0x20000;VTABLE=STORE+0x100

class Flags(fragment.GammaFragment):
 def __init__(self,source):
  super().__init__(source);self.overrides={};self.settings_reads=[]
  self.write(STORE,'<Q',VTABLE);self.write(VTABLE,'<16Q',*([READ]*16))
 def _step(self,uc,pc,size,user):
  if pc==READ:
   key=uc.reg_read(UC_ARM64_REG_W1);dest=uc.reg_read(UC_ARM64_REG_X2);before=self.read(dest,'<I')[0]
   self.settings_reads.append(dict(key=key,before=before,return_to=uc.reg_read(UC_ARM64_REG_LR)))
   if key in self.overrides:self.write(dest,'<I',self.overrides[key])
   uc.reg_write(UC_ARM64_REG_X0,0);uc.reg_write(UC_ARM64_REG_PC,uc.reg_read(UC_ARM64_REG_LR));self.instructions+=1;return
  return super()._step(uc,pc,size,user)
 def defaults(self,fill=0):
  self.uc.mem_write(OBJECT,bytes([fill])*0x10000);self.begin=0x3c2720;self.end=0x3c2764;self.call(x0=OBJECT)
  return self.read(OBJECT+15632,'<I')[0]
 def override(self,values):
  self.begin=0x3c2770;self.end=0x3c3090;self.overrides=values;self.settings_reads=[];self.call(x0=OBJECT,x1=STORE)
  return self.read(OBJECT+15632,'<I')[0]
 def constructor_read_fragment(self,word):
  self.write(OBJECT+15632,'<I',word);self.begin=0x35e450;self.end=0x35e468
  self.uc.reg_write(UC_ARM64_REG_X12,OBJECT);self.uc.reg_write(UC_ARM64_REG_X20,OBJECT+0x10000)
  self.uc.emu_start(self.begin,self.end,timeout=100000,count=100)
  assert self.uc.reg_read(UC_ARM64_REG_PC)==self.end
  return self.read(OBJECT+0x10000+620,'<2I')

engine=Flags(P.parent/'kernel281/camera.qcom.so-private');defaults=[engine.defaults(fill) for fill in [0,255]]
assert all((word&((1<<22)-1))==0x33c91 for word in defaults)
assert all(engine.constructor_read_fragment(word)==(0,0) for word in defaults)
for ignore,hardcoded in [(0,0),(1,0),(0,1),(1,1)]:
 assert engine.constructor_read_fragment((ignore<<18)|(hardcoded<<19))==(ignore,hardcoded)
engine.defaults();baseline=engine.override({});reads=engine.settings_reads.copy();assert baseline&((1<<18)|(1<<19))==0
matches={18:[],19:[]}
for key in sorted({r['key'] for r in reads}):
 engine.defaults();word=engine.override({key:1})
 for bit in matches:
  if word&(1<<bit):matches[bit].append(key)
assert all(len(keys)==1 for keys in matches.values()),matches
for ignore,hardcoded in [(0,0),(1,0),(0,1),(1,1)]:
 engine.defaults();word=engine.override({matches[18][0]:ignore,matches[19][0]:hardcoded})
 assert engine.constructor_read_fragment(word)==(ignore,hardcoded)
raw=(P.parent/'kernel281/camera.qcom.so-private').read_bytes()
# The constructor log arguments W6/W7 read the two object slots and identify
# them in this order; the source version is not used to guess their offsets.
log=raw[0x1058d:raw.index(b'\0',0x1058d)].decode();assert 'm_ignoreChromatixRGammaFlag %d, m_useHardcodedGamma %d' in log
assert struct.unpack_from('<II',raw,0x35e498)==(0xb9426e86,0x9a8006c3)
assert struct.unpack_from('<I',raw,0x35e4a0)[0]==0xb9427287
report=dict(stage=351,source_retained_from281=True,defaults_function=['0x3c2720','0x3c2764'],
 override_function=['0x3c2770','0x3c3090'],constructor_read_fragment=['0x35e450','0x35e468'],
 factory_settings_bitfield_offset=15632,constructor_slots=[620,624],
 flags=[dict(name='ignoreChromatixRGammaFlag',bit=18,compiled_default=False,override_key=hex(matches[18][0])),dict(name='useHardcodedGamma',bit=19,compiled_default=False,override_key=hex(matches[19][0]))],
 name_binding_from_actual_constructor_log_arguments=True,default_mask_verified_from_zero_and_all_one_inputs=True,
 all_four_override_and_constructor_combinations_verified=True,virtual_settings_reader_stub_only=True,
 override_read_calls_per_function=len(reads),original_instructions_executed=engine.instructions,
 no_android_code_run_natively=True,target_android_runtime_property_values_not_observed=True,
 tuning_reserve_still_needed=True,phone_changed_by_this_check=False,passed=True)
(P/'static-settings-reads-private.json').write_text(json.dumps(reads,indent=2)+'\n')
(HERE/'static-flags-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
