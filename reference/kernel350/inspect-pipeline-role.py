"""Record scoped source evidence and factory module constructor bindings."""
from pathlib import Path
import json,struct
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
raw=(P.parent/'kernel281/camera.qcom.so-private').read_bytes()
offset=struct.unpack_from('<Q',raw,40)[0];stride,count=struct.unpack_from('<HH',raw,58);relr=set();rela={}
for i in range(count):
 section=struct.unpack_from('<IIQQQQIIQQ',raw,offset+i*stride)
 if section[1] in [19,0x6fffff00]:
  where=0
  for pos in range(section[4],section[4]+section[5],8):
   value=struct.unpack_from('<Q',raw,pos)[0]
   if not value&1:relr.add(value);where=value+8
   else:
    for bit in range(1,64):
     if value&(1<<bit):relr.add(where+(bit-1)*8)
    where+=63*8
 if section[1]==4:
  for pos in range(section[4],section[4]+section[5],section[9]):
   address,info,addend=struct.unpack_from('<QQq',raw,pos)
   if info&0xffffffff==1027:rela[address]=addend
phoff=struct.unpack_from('<Q',raw,32)[0];phstride,phcount=struct.unpack_from('<HH',raw,54)
segments=[struct.unpack_from('<II6Q',raw,phoff+i*phstride) for i in range(phcount)]
symbols={int(line.split()[0],16):line.split(' ',2)[2] for line in (P/'hal-symbols-private.txt').read_text().splitlines() if len(line.split(' ',2))==3}
records=[]
for address,name,tag in [(0x34f8d0,'IPEColorTransform12',33),(0x35e238,'IPELTM13',34),(0x350368,'IPEColorCorrection13',35),(0x351bd8,'IPEGamma15',36)]:
 pattern=struct.pack('<4IQ',tag,0,7,0,address);at=raw.index(pattern);assert raw.find(pattern,at+1)==-1
 segment=next(s for s in segments if s[0]==1 and s[2]<=at<s[2]+s[5]);pointer=segment[3]+at-segment[2]+16
 assert name+'::Create(' in symbols[address]
 assert pointer in relr or rela.get(pointer)==address,(name,hex(pointer))
 records.append(dict(module=name,tag=tag,constructor=hex(address),constructor_symbol=symbols[address],registry_pointer_slot=hex(pointer),
  relocation='RELR' if pointer in relr else 'RELA',opaque_registry_words_not_interpreted_as_runtime_enable=True))
assert all(int(records[i+1]['registry_pointer_slot'],16)-int(records[i]['registry_pointer_slot'],16)==24 for i in range(3))
facts=[]
def fact(file,needles,interpretation):
 lines=(P/'sources'/file).read_text().splitlines();anchors=[]
 for needle in needles:
  found=[i+1 for i,line in enumerate(lines) if needle in line];assert found,(file,needle)
  anchors.append(dict(needle=needle,lines=found))
 facts.append(dict(file=file,anchors=anchors,interpretation=interpretation,scope='pinned published source, not observed target Android runtime'))
fact('camxifegamma16.cpp',['IFEDynamicEnableMask','TonemapModeContrastCurve','gammaOutput.gammaG'],
 'IFE enable also depends on runtime mask and tonemap mode; enabled tuning alone is insufficient. The exported Gamma output is its 64 green base nodes.')
fact('camxipenode.cpp',['IPENode::GetGammaOutput(','IPENode::GetGammaPreCalculationOutput(','case ISPIQModuleType::IPELTM:','case ISPIQModuleType::IPEGamma:'],
 'The IPE node consumes upstream IFE/BPS Gamma and distinguishes this from later Gamma15 pre-calculation metadata; LTM is classified before the post-LTM Gamma/CCM commands.')
fact('ltm13setting.cpp',['InverseGamma(gamma,','pReserveData->igamma_en'],
 'LTM constructs inverse Gamma from the upstream curve, with a separate reserve-data enable. It cannot be modelled as plain composition of the two Gamma curves.')
fact('camxipeltm13.cpp',['m_useHardcodedGamma','m_ignoreChromatixRGammaFlag','moduleCfg.RGAMMA_EN = 0'],
 'Static settings can replace the upstream curve with a hardcoded one or disable RGamma despite the Chromatix reserve value. Target values have not yet been recovered.')
for name in ['camxipepipelinetitan170.cpp','camxipepipelinetitan175.cpp']:
 text=(P/'sources'/name).read_text();order=['ISPIQModuleType::IPECST','ISPIQModuleType::IPELTM','ISPIQModuleType::IPEColorCorrection','ISPIQModuleType::IPEGamma','ISPIQModuleType::IPEChromaEnhancement']
 assert [text.index(s) for s in order]==sorted(text.index(s) for s in order)
 fact(name,order,'Published hardware-order list places CST, LTM, CCM, Gamma, chroma enhancement in this order. This does not identify the target Titan version or actual runtime enable state.')
report=dict(stage=350,source_manifest='primary-sources.json',factory_binary_evidence='../kernel286/register-contract-validation.json',
 factory_constructor_bindings=records,source_facts=facts,registry_neighborhood_not_claimed_as_full_physical_graph=True,
 target_titan_version_not_inferred_from_vfe_driver_filename=True,actual_android_runtime_masks_and_overrides_not_observed=True,
 need_ltm_reserve_and_ipe_ccm_and_static_settings_before_final_tone_default=True,
 simple_gamma_composition_not_accepted_as_final_oem_output=True,phone_changed=False,passed=True)
(HERE/'pipeline-role-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(constructor_bindings=len(records),source_facts=len(facts),scope='source chain and retained constructor relocations; runtime overrides pending',passed=True),indent=2))
