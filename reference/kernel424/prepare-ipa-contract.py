from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel423/ipa-contract.cpp').read_text()
needle=' auto first=process(1,32);assert(!prepare(1,first));'
replacement=''' // A structurally valid legacy BHIST has no BG/lux. It must not drop
 // the image or fabricate the first numerical history.
 const uint32_t legacy=sizeof(v4l2_isp_buffer)+sizeof(camss_stats_bhist);
 auto noLux=[&](uint32_t sof){
  envelope->data_size=sizeof(*hist);unsigned n=observed.calls;
  ipa->processStats(1,sof,100,legacy,ipa::camss::SensorContext{true,500,32,0});
  envelope->data_size=used-sizeof(*envelope);
  assert(observed.calls==n+1&&!observed.result.status&&observed.result.ipeToken&&!observed.result.luxValid);
  return observed.result.ipeToken;
 };
 auto missingFirst=noLux(0);int initialMissing=prepare(0,missingFirst);
 std::cerr<<"MISSING_LUX initial status="<<initialMissing<<std::endl;
 assert(!initialMissing&&packet.empty()&&!fresh&&revision==0);
 ipa->frameProcessed(1,0,missingFirst,true);
 auto first=process(1,32);assert(!prepare(1,first));'''
assert source.count(needle)==1;source=source.replace(needle,replacement)
needle='  std::ofstream output(argv[4],std::ios::binary);'
replacement='''  auto gap=noLux(5);assert(!prepare(5,gap)&&packet==committed&&!fresh&&revision==2);
  ipa->frameProcessed(1,5,gap,true);
  assert(!prepare(6,0)&&packet==committed&&!fresh&&revision==2);
  auto recovered=process(6,128);assert(!prepare(6,recovered)&&fresh&&revision==3);
  ipa->frameProcessed(1,6,recovered,true);committed=packet;
  assert(!prepare(7,0)&&packet==committed&&!fresh&&revision==3);
  std::ofstream output(argv[4],std::ios::binary);'''
assert source.count(needle)==1;source=source.replace(needle,replacement)
(HERE/'ipa-contract.cpp').write_text(source)
