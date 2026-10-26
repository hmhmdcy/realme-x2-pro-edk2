 uint32_t bytes=0;auto *parameterMemory=static_cast<uint8_t*>(mmap(nullptr,capacity,PROT_READ,MAP_SHARED,pfd.get(),0));assert(parameterMemory!=MAP_FAILED);
 auto queue=[&](uint32_t rev){
  assert(!ipa->prepareParameters(1,1,rev,&bytes));camss_params_ife_gtm g{};bool found=false;
  for(size_t at=sizeof(v4l2_isp_buffer);at<bytes;){v4l2_isp_block_header h;std::memcpy(&h,parameterMemory+at,sizeof h);assert(h.size>=8&&at+h.size<=bytes);
   if(h.type==CAMSS_PARAMS_IFE_GTM){assert(!found&&h.size==sizeof g);std::memcpy(&g,parameterMemory+at,sizeof g);found=true;}
   assert(h.type!=CAMSS_PARAMS_COLOR_CORRECT);at+=h.size;}
  assert(found&&g.cookie&&!g.enabled);ipa->parametersApplied(1,0,rev);return g;
 };
 auto initial=queue(0);assert(initial.cookie==1);
 constexpr uint32_t used=baseUsed+sizeof(camss_stats_ife_gtm);
 camss_stats_ife_gtm receipt{};receipt.header={CAMSS_STATS_IFE_GTM,0,sizeof receipt};receipt.cookie=1;receipt.generation=1;receipt.status=1;
 auto process=[&](uint32_t sof,int cct){
  envelope->data_size=used-sizeof(*envelope);std::memcpy(memory+baseUsed,&receipt,sizeof receipt);
  unsigned n=observed.calls;ipa->processStats(1,sof,100,used,ipa::camss::SensorContext{true,500,32,0});
  std::cerr<<"FRONT_STATS sof="<<sof<<" status="<<observed.result.status<<" token="<<observed.result.ipeToken<<std::endl;
  assert(observed.calls==n+1&&!observed.result.status&&observed.result.ipeToken);
  assert(observed.metadata.get(controls::ColourTemperature)==cct);
  return observed.result;
 };
 std::vector<uint8_t> packet;uint64_t revision=0;bool fresh=false;
 auto prepare=[&](uint32_t sof,uint64_t token){assert(!ipa->prepareIpeParameters(1,sof,token,&packet,&revision,&fresh));assert(packet.size()==6008);qcom_ipe_a5_frame_params p;std::memcpy(&p,packet.data(),sizeof p);assert(p.colour.modules==7);return p;};
 auto first=process(0,3000);assert(first.ispUpdate.valid);auto boot=prepare(0,first.ipeToken);assert(!fresh&&!revision&&!boot.flags);ipa->frameProcessed(1,0,first.ipeToken,true);
 auto ready=queue(first.ispUpdate.revision);receipt.cookie=ready.cookie;receipt.generation=2;receipt.status=1;receipt.bank=1;
 ControlList change(controls::controls);change.set(controls::ColourTemperature,8000);ipa::camss::AutoIspUpdate update{};
 assert(ipa->applyIspControls(1,1,change,&update)==-EAGAIN);
 auto one=process(1,3000);auto p1=prepare(1,one.ipeToken);assert(fresh&&revision==1&&p1.flags==3);ipa->frameProcessed(1,1,one.ipeToken,false);
 auto two=process(2,3000);
 assert(!ipa->applyIspControls(1,3,change,&update)&&update.valid);auto future=queue(update.revision);
 // Controls requested after observation cannot alter that observation's CCM.
 auto p2=prepare(2,two.ipeToken);assert(fresh&&revision==1&&!std::memcmp(&p1.colour.cc,&p2.colour.cc,sizeof p1.colour.cc));ipa->frameProcessed(1,2,two.ipeToken,true);
 auto three=process(3,3000);auto p3=prepare(3,three.ipeToken);assert(fresh&&revision==2&&!std::memcmp(&p2.colour.cc,&p3.colour.cc,sizeof p2.colour.cc));ipa->frameProcessed(1,3,three.ipeToken,true);
 ControlList manual(controls::controls);const std::array<float,9> matrix{0,0,1,0,1,0,1,0,0};manual.set(controls::ColourCorrectionMatrix,Span<const float,9>(matrix));update={};
 assert(ipa->applyIspControls(1,4,manual,&update)==-EAGAIN);
 receipt.cookie=future.cookie;receipt.generation=3;receipt.bank=0;
 auto four=process(4,8000);auto p4=prepare(4,four.ipeToken);assert(fresh&&revision==3&&std::memcmp(&p3.colour.cc,&p4.colour.cc,sizeof p3.colour.cc));ipa->frameProcessed(1,4,four.ipeToken,true);
 assert(!ipa->applyIspControls(1,5,manual,&update)&&update.valid);future=queue(update.revision);
 auto five=process(5,8000);auto p5=prepare(5,five.ipeToken);assert(!std::memcmp(&p4.colour.cc,&p5.colour.cc,sizeof p4.colour.cc));ipa->frameProcessed(1,5,five.ipeToken,true);
 receipt.cookie=future.cookie;receipt.generation=4;receipt.bank=1;
 auto six=process(6,8000);auto p6=prepare(6,six.ipeToken);assert(p6.colour.cc.matrix[2]==128&&p6.colour.cc.matrix[6]==128&&!p6.colour.cc.matrix[0]);ipa->frameProcessed(1,6,six.ipeToken,true);
 ipa->stop();assert(!ipa->start(2,start,&converted));assert(ipa->prepareIpeParameters(2,0,0,&packet,&revision,&fresh)==-ENODATA);
 ipa->stop();ipa->unmapBuffers({1,100});ipa.reset();dlclose(handle);munmap(memory,capacity);munmap(parameterMemory,capacity);
 std::cout<<"FRONT_IPA_PASS disabled_gtm=1 no_ife_ccm=1 same_frame_cct=1 future_controls_frozen=1 failed_history=1 manual_ipe=1 restart=1 frames=7\n";
}
