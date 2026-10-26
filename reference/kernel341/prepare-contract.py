from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel340/ccm-runtime-contract.cpp').read_text()
s=s.replace('assert(used==(enabled?96u:56u))','assert(used==(enabled?1888u:1848u))')
s=s.replace('assert(enabled&&!pending);','assert(!pending);').replace('if(enabled)assert(pending);','assert(pending);')
s=s.replace('else if(!pending&&enabled)++noops;','else if(!pending)++noops;')
s=s.replace('process(sof,100,32);assert(!pending);process(++sof,3000,900);assert(!pending);','process(sof,3000,900);assert(!pending);process(++sof,3000,900);assert(!pending);')
s=s.replace('assert(used==96);','assert(used==(enabled?96u:56u)||used==(enabled?1888u:1848u));')
s=s.replace('std::array<uint8_t,96> before;std::copy(parameters,parameters+96,before.begin());process(4,3000,900);assert(!std::memcmp(before.data(),parameters,96));','std::vector<uint8_t> before(parameters,parameters+used);process(4,3000,900);assert(!std::memcmp(before.data(),parameters,used));')
# Manual CCM remains optional. Dynamic LSC must still track CCT on a factory-
# disabled front CCM profile, without requiring a made-up matrix control.
a='''  auto request=[&](const ControlList &controls,const std::string &kind){'''
b=''' }
 auto request=[&](const ControlList &controls,const std::string &kind){'''
# Move only the common request lambda and common CCT/zero-gain checks out of
# the CCM-specific branch; retain the independent manual-matrix case there.
start=s.index(' if(enabled){\n  const std::array<float,9> manual');end=s.index('  ControlList change(controls::controls);',start)
lambdaText=s[s.index('  auto request=',start):end]
s=s[:start]+lambdaText+''' ControlList change(controls::controls);
 if(enabled){
  const std::array<float,9> manual{0,0,1,0,.75f,0,1,0,0};
'''+s[end:]
s=s.replace('  ControlList change(controls::controls);change.set(controls::ColourCorrectionMatrix','  change.set(controls::ColourCorrectionMatrix')
s=s.replace('  change.clear();change.set(controls::ColourTemperature,2850);',' }\n  change.clear();change.set(controls::ColourTemperature,2850);')
s=s.replace('  assert(noops);\n }','  assert(noops);')
s=s.replace('RUNTIME_CCM_CONTRACT_PASS','DYNAMIC_LSC_CONTRACT_PASS').replace('RUNTIME_CCM_REJECT_PASS','DYNAMIC_LSC_REJECT_PASS')
(HERE/'dynamic-lsc-contract.cpp').write_text(s);print('Prepared dynamic LSC/CCM transaction contract from retained340 cases.')
