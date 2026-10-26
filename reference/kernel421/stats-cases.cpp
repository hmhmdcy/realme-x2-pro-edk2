int main(){unsigned cases=0;
 for(unsigned kind=0;kind<10;++kind){CamssVfeData d;FrameBuffer statistics;d.pendingStats_[100]={1,&statistics,true};ipa::camss::Statistics result;ControlList metadata;
  if(kind==1)result.ispUpdate.valid=false;
  if(kind==2)d.images_.clear();
  if(kind==3)result.status=-EINVAL;
  if(kind==4)d.epoch_=2;
  if(kind==5)d.pendingStats_.clear();
  if(kind==6)d.pendingStats_[100].submitted=false;
  if(kind==7)d.pendingStats_[100].sof=2;
  if(kind==8)d.stopOnFinish=true;
  if(kind==9)d.ipaObject.stopDuringPrepare=true;
  d.statsProcessed(1,1,100,result,metadata);
  if(kind>=4 && kind<=7)assert(d.statsObject.queued==0 && d.ipaObject.prepares==0);
  else if(kind==8)assert(d.paired==1 && !d.fallback && !d.statsObject.queued && !d.ipaObject.prepares);
  else if(kind==9)assert(d.paired==1 && !d.fallback && !d.statsObject.queued && d.ipaObject.prepares==1 && !d.paramsObject.queued);
  else {assert(d.fallback==0 && d.statsObject.queued==1);if(kind==0 || kind==1)assert(d.paired==1);if(kind==2)assert(d.histograms_.count(1));}
  ++cases;
 }
 {CamssVfeData d;d.ipaObject.stopDuringPrepare=true;d.queueIspUpdate({true,1,1,1});assert(!d.paramsObject.queued && d.ipaObject.prepares==1);++cases;}
 std::printf("IPE_STATS_REENTRY_MODEL cases=%u passed=1\n",cases);
}
