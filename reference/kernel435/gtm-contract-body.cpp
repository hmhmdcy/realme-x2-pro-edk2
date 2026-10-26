 uint32_t bytes=0;auto *parameterMemory=static_cast<uint8_t*>(mmap(nullptr,capacity,PROT_READ,MAP_SHARED,pfd.get(),0));assert(parameterMemory!=MAP_FAILED);
 auto queue=[&](uint32_t rev){
  assert(!ipa->prepareParameters(1,1,rev,&bytes));camss_params_ife_gtm g{};bool found=false;
  v4l2_isp_buffer e;std::memcpy(&e,parameterMemory,sizeof e);assert(e.data_size+sizeof e==bytes);
  for(size_t at=sizeof e;at<bytes;){v4l2_isp_block_header h;std::memcpy(&h,parameterMemory+at,sizeof h);assert(h.size>=8&&at+h.size<=bytes);
   if(h.type==CAMSS_PARAMS_IFE_GTM){assert(!found&&h.size==sizeof g&&!h.flags);std::memcpy(&g,parameterMemory+at,sizeof g);found=true;}at+=h.size;}
  assert(found&&g.cookie);ipa->parametersApplied(1,0,rev);return g;
 };
 auto initial=queue(0);assert(initial.cookie==1&&initial.enabled==0);
 constexpr uint32_t used=baseUsed+sizeof(camss_stats_ife_gtm);
 camss_stats_ife_gtm receipt{};receipt.header={CAMSS_STATS_IFE_GTM,0,sizeof receipt};receipt.cookie=1;receipt.generation=1;receipt.status=1;
 auto stamp=[&](){envelope->data_size=used-sizeof(*envelope);std::memcpy(memory+baseUsed,&receipt,sizeof receipt);};
 auto process=[&](uint32_t sof){stamp();unsigned calls=observed.calls;ipa->processStats(1,sof,100,used,ipa::camss::SensorContext{true,500,32,0});assert(observed.calls==calls+1);return observed.result;};
 auto bad=receipt;receipt.cookie=999;auto rejected=process(0);assert(rejected.status==-ESTALE&&!rejected.parametersKnown&&!rejected.ipeToken);receipt=bad;
 auto first=process(0);assert(!first.status&&first.ipeToken&&first.ispRevision==0&&first.ispUpdate.valid);
 std::vector<uint8_t> packet,committed;uint64_t revision=0;bool fresh=false;
 auto prepare=[&](uint32_t sof,uint64_t token){return ipa->prepareIpeParameters(1,sof,token,&packet,&revision,&fresh);};
 assert(!prepare(0,first.ipeToken)&&packet.size()==6008&&!fresh&&revision==0);
 assert(reinterpret_cast<const qcom_ipe_a5_frame_params*>(packet.data())->flags==0);
 ipa->frameProcessed(1,0,first.ipeToken,true);
 auto second=queue(first.ispUpdate.revision);assert(second.cookie==2&&second.enabled==1);
 auto stillInitial=process(1);assert(!stillInitial.status&&stillInitial.ispRevision==0&&!stillInitial.ispUpdate.valid);
 assert(!prepare(1,stillInitial.ipeToken)&&!fresh&&revision==0);ipa->frameProcessed(1,1,stillInitial.ipeToken,true);
 receipt.cookie=2;receipt.generation=2;receipt.status=3;receipt.bank=1;
 auto applied=process(2);assert(!applied.status&&applied.ispRevision==1&&applied.ispUpdate.valid);
 assert(!prepare(2,applied.ipeToken)&&fresh&&revision==1&&packet.size()==6008);
 auto third=queue(applied.ispUpdate.revision);assert(third.cookie==3&&third.enabled==1);
 ControlList deferredControls(controls::controls);ipa::camss::AutoIspUpdate deferred{};
 assert(ipa->applyIspControls(1,3,deferredControls,&deferred)==-EAGAIN);
 ipa->frameProcessed(1,2,applied.ipeToken,false);
 auto oldVersion=process(3);assert(!oldVersion.status&&oldVersion.ispRevision==1);
 assert(!prepare(3,oldVersion.ipeToken)&&fresh&&revision==1);ipa->frameProcessed(1,3,oldVersion.ipeToken,true);committed=packet;
 receipt.cookie=3;receipt.generation=3;receipt.bank=0;
 auto newest=process(4);assert(!newest.status&&newest.ispRevision==2&&!newest.ispUpdate.valid);
 assert(!ipa->applyIspControls(1,5,deferredControls,&deferred));
 assert(!prepare(4,newest.ipeToken)&&fresh&&revision==2);
 ipa->frameProcessed(99,4,newest.ipeToken,true);assert(prepare(5,0)==-ENODATA);
 const uint32_t legacy=sizeof(v4l2_isp_buffer)+sizeof(camss_stats_bhist);std::vector<uint8_t> grid(memory+legacy,memory+baseUsed);
 auto noLux=[&](uint32_t sof){
  envelope->data_size=sizeof(camss_stats_bhist)+sizeof receipt;std::memcpy(memory+legacy,&receipt,sizeof receipt);
  ipa->processStats(1,sof,100,legacy+sizeof receipt,ipa::camss::SensorContext{true,500,32,0});
  std::memcpy(memory+legacy,grid.data(),grid.size());assert(!observed.result.status&&observed.result.ipeToken&&!observed.result.luxValid);return observed.result;
 };
 auto missing=noLux(5);assert(prepare(5,missing.ipeToken)==-EAGAIN); // old held LTM cannot consume a different upstream GTM
 ipa->frameProcessed(1,4,newest.ipeToken,false);ipa->frameProcessed(1,5,missing.ipeToken,false);
 auto recovered=process(6);assert(!recovered.status&&recovered.ispRevision==2);
 assert(!prepare(6,recovered.ipeToken)&&fresh&&revision==2);ipa->frameProcessed(1,6,recovered.ipeToken,true);committed=packet;
 auto held=noLux(7);assert(!prepare(7,held.ipeToken)&&packet==committed&&!fresh&&revision==2);ipa->frameProcessed(1,7,held.ipeToken,true);
 auto saved=receipt;receipt.generation=99;rejected=process(8);assert(rejected.status==-EPROTO&&!rejected.ipeToken);receipt=saved;
 auto resumed=process(8);assert(!resumed.status&&resumed.ipeToken&&resumed.ispRevision==2);ipa->frameProcessed(1,8,resumed.ipeToken,false);
 ipa->stop();assert(!ipa->start(2,start,&converted));assert(ipa->prepareIpeParameters(2,0,0,&packet,&revision,&fresh)==-ENODATA);
 assert(ipa->prepareIpeParameters(1,6,recovered.ipeToken,&packet,&revision,&fresh)==-ESTALE);
 ipa->stop();ipa->unmapBuffers({1,100});ipa.reset();dlclose(handle);munmap(memory,capacity);munmap(parameterMemory,capacity);
 std::cout<<"GTM_IPA_CONTRACT passed=1 actual_module=1 submission_not_ack=1 bootstrap_no_math_commit=1 physical_vs_numeric_history=1 incompatible_hold_rejected=1 matching_hold_kept=1\n";
}
