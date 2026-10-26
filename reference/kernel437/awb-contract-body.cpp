 uint32_t bytes=0;auto *parameterMemory=static_cast<uint8_t*>(mmap(nullptr,capacity,PROT_READ,MAP_SHARED,pfd.get(),0));assert(parameterMemory!=MAP_FAILED);
 auto queue=[&](uint32_t rev){
  assert(!ipa->prepareParameters(1,1,rev,&bytes));camss_params_ife_gtm g{};bool found=false;
  v4l2_isp_buffer e;std::memcpy(&e,parameterMemory,sizeof e);assert(e.data_size+sizeof e==bytes);
  for(size_t at=sizeof e;at<bytes;){v4l2_isp_block_header h;std::memcpy(&h,parameterMemory+at,sizeof h);assert(h.size>=8&&at+h.size<=bytes);
   if(h.type==CAMSS_PARAMS_IFE_GTM){assert(!found&&h.size==sizeof g);std::memcpy(&g,parameterMemory+at,sizeof g);found=true;}at+=h.size;}
  assert(found&&g.cookie);ipa->parametersApplied(1,0,rev);return g;
 };
 auto initial=queue(0);assert(initial.cookie==1);
 constexpr uint32_t used=baseUsed+sizeof(camss_stats_ife_gtm);
 camss_stats_ife_gtm receipt{};receipt.header={CAMSS_STATS_IFE_GTM,0,sizeof receipt};receipt.cookie=1;receipt.generation=1;receipt.status=1;
 std::optional<std::pair<uint32_t,camss_params_ife_gtm>> pending;
 unsigned lockedWaiting=0,lockedValid=0,recoveryCalculations=0;
 auto process=[&](uint32_t sof,int expected,bool missing=false){
  if(pending && pending->first==sof){receipt.cookie=pending->second.cookie;++receipt.generation;receipt.bank^=1;receipt.status=3;pending.reset();}
  const uint32_t payload=missing?sizeof(v4l2_isp_buffer)+sizeof(camss_stats_bhist):baseUsed;
  envelope->data_size=payload+sizeof(receipt)-sizeof(*envelope);std::memcpy(memory+payload,&receipt,sizeof receipt);
  unsigned calls=observed.calls;ipa->processStats(1,sof,100,payload+sizeof receipt,ipa::camss::SensorContext{true,500,32,0});
  if(missing)std::memcpy(memory+sizeof(v4l2_isp_buffer)+sizeof(camss_stats_bhist),grid.data(),grid.size());
  assert(observed.calls==calls+1&&!observed.result.status);
  if(expected<0 && observed.result.awbRegions)++recoveryCalculations;
  const bool expectLocked=expected<0 ? recoveryCalculations>=3 : bool(expected);
  bool locked=observed.metadata.get(controls::AwbLocked).value_or(false);
  std::cerr<<"AWB_CASE sof="<<sof<<" calculated="<<observed.result.awbRegions<<" pending="<<bool(pending)<<" locked="<<locked<<" expected="<<expectLocked<<std::endl;
  assert(locked==expectLocked);
  if(locked && pending)++lockedWaiting;
  if(locked && observed.result.awbRegions)++lockedValid;
  if(observed.result.ipeToken)ipa->frameProcessed(1,sof,observed.result.ipeToken,false);
  if(observed.result.ispUpdate.valid){assert(!pending);pending=std::make_pair(sof+2,queue(observed.result.ispUpdate.revision));}
 };
 for(uint32_t sof=0;sof<10;++sof)process(sof,sof>=4);
 assert(lockedWaiting>=2&&lockedValid>=2);
 process(10,false,true);
 for(uint32_t sof=11;sof<20;++sof)process(sof,-1);
 assert(recoveryCalculations>=3);
 ipa->stop();assert(!ipa->start(2,start,&converted));
 assert(!ipa->prepareParameters(2,1,0,&bytes));ipa->parametersApplied(2,0,0);
 receipt.cookie=1;receipt.generation=1;receipt.bank=0;receipt.status=1;
 envelope->data_size=used-sizeof(*envelope);std::memcpy(memory+baseUsed,&receipt,sizeof receipt);
 ipa->processStats(2,0,100,used,ipa::camss::SensorContext{true,500,32,0});
 assert(!observed.result.status&&!observed.metadata.get(controls::AwbLocked).value_or(true));
 ipa->stop();ipa->unmapBuffers({1,100});ipa.reset();dlclose(handle);munmap(memory,capacity);munmap(parameterMemory,capacity);
 std::cout<<"AWB_STATUS_CONTRACT passed=1 pending_gtm_preserves_applied_lock=1 missing_bg_invalidates=1 restart_resets=1\n";
}
