int main()
{
 unsigned cases=0;
 for(unsigned kind=0;kind<11;++kind){CamssVfeData d;Request request;FrameBuffer image,raw,ife;ife.sof=1;raw.sof=2;
  auto token=d.add(&request,&image,&raw,&ife);
  if(kind==1)d.requests_[&request].imageFinished=false;
  if(kind==2)d.requests_[&request].rawReady=false;
  if(kind==3 || kind==4)d.rawStarts_.clear();
  if(kind==5)d.rawStarts_[raw.sof]+=2000000;
  if(kind==6)d.requests_[&request].failed=true;
  if(kind==7)d.running_=false;
  if(kind==8)d.processedEnabled_=false;
  if(kind==9)d.ipe_=nullptr;
  if(kind==10)d.rawEnabled_=false;
  d.tryComplete(&request,kind==4);
  if(kind==1 || kind==2 || kind==3){assert(d.object.receipts.empty() && d.object.history.pending(token) && !d.callbacks.requests);}
  else {const bool success=kind==0 || kind==10;assert(d.object.receipts==std::vector<int>{success?1:0});
   assert(bool(d.object.history.committed())==success && !d.object.history.pending(token));
   assert(d.callbacks.requests==1 && d.internalRequests_.empty() && d.freeImages_.size()==1);
   d.tryComplete(&request);assert(d.object.receipts.size()==1 && d.callbacks.requests==1);}
  ++cases;
 }
 {CamssVfeData d;Request a,b;FrameBuffer ia,ra,fa,ib,rb,fb;fa.sof=1;ra.sof=1;fb.sof=2;rb.sof=2;
  d.add(&a,&ia,&ra,&fa);d.add(&b,&ib,&rb,&fb);d.tryComplete(&b);d.tryComplete(&a);
  assert((d.object.receipts==std::vector<int>{1,2}) && d.object.history.committed()->sof==2);++cases;}
 std::printf("IPE_AGGREGATE_MODEL cases=%u passed=1\n",cases);
}
