using namespace libcamera;
struct Receiver {
 CamssIpe *ipe;FrameBuffer *input,*output;unsigned good=0,bad=0;bool requireClosed=false,reenterStop=false,requeue=false;
 void ready(FrameBuffer *a,FrameBuffer *b,bool success){
  assert(a==input && b==output);assert(input->metadata().sequence==71 && input->metadata().timestamp==998877);
  if(requireClosed)assert(!current->open);
  if(success)++good;else ++bad;
  if(reenterStop)ipe->stop();
  if(requeue && success){requeue=false;assert(!ipe->queue(input,output));}
 }
};
static auto media(){return std::make_shared<MediaDevice>();}
static FrameBuffer buffer(int id){return FrameBuffer({{std::make_shared<int>(id),0,460800}});}
int main(){
 unsigned cases=0;
 for(int legacy=0;legacy<2;legacy++)for(int failure=1;failure<=7;failure++){
  nextFaults={};nextFaults.startStep=failure;nextFaults.legacy=legacy;
  CamssIpe ipe("fake",media());assert(ipe.start({},4)<0);assert(!current->open && !V4L2Request::live);dispatch();++cases;
 }
 for(unsigned failure=0;failure<3;failure++){
  nextFaults={};nextFaults.badShape=failure==0;nextFaults.noMediaRequests=failure==1;nextFaults.allocate=failure==2;
  CamssIpe ipe("fake",media());assert(ipe.start({},4)<0 && !current->open && !V4L2Request::live);++cases;
 }
 std::array<unsigned,3> order={0,1,2};
 do{
  nextFaults={};CamssIpe ipe("fake",media());assert(!ipe.start({},2));
  auto input=buffer(1),output=buffer(2);Receiver r{&ipe,&input,&output};ipe.processed.connect(&r,&Receiver::ready);
  qcom_ipe_a5_frame_params params{};params.version=1;params.size=sizeof(params);params.gamma.base[0][0]=73;
  assert(!ipe.queue(&input,&output,&params));params.gamma.base[0][0]=99;
  auto *req=ipe.jobs_.at(&output).request;assert(req && V4L2Request::live==2);
  auto *copy=reinterpret_cast<const qcom_ipe_a5_frame_params *>(req->payload.data());assert(copy->gamma.base[0][0]==73);
  for(unsigned i=0;i<3;i++){
   if(order[i]==0)ipe.device_.output()->returnOne();
   if(order[i]==1)ipe.device_.capture()->returnOne();
   if(order[i]==2)req->returnOne();
   dispatch();assert(r.good==(i==2) && !r.bad);
  }
  assert(FrameBuffer::live==2 && ipe.jobs_.empty() && ipe.freeRequests_.size()==2 && !ipe.watchdog_.isRunning());
  ipe.stop();assert(!V4L2Request::live && !current->open);++cases;
 }while(std::next_permutation(order.begin(),order.end()));
 for(unsigned failure=0;failure<4;failure++){
  nextFaults={};if(failure<2)nextFaults.queueSide=failure;else nextFaults.requestQueue=failure==2;
  CamssIpe ipe("fake",media());assert(!ipe.start({},2));auto input=buffer(1),output=buffer(2);
  Receiver r{&ipe,&input,&output,0,0,true};ipe.processed.connect(&r,&Receiver::ready);
  if(failure==3){current->faults.controls=true;assert(ipe.queue(&input,&output)<0 && !r.bad && ipe.jobs_.empty());ipe.stop();}
  else {assert(!ipe.queue(&input,&output));assert(r.bad==1 && !r.good && !current->open);}
  dispatch();assert(!V4L2Request::live && FrameBuffer::live==2);++cases;
 }
 for(unsigned mask=0;mask<4;mask++){
  nextFaults={};nextFaults.streamOffMask=mask;CamssIpe ipe("fake",media());assert(!ipe.start({},2));
  auto input=buffer(1),output=buffer(2);Receiver r{&ipe,&input,&output,0,0,true};ipe.processed.connect(&r,&Receiver::ready);
  assert(!ipe.queue(&input,&output));ipe.stop();dispatch();assert(r.bad==1 && !r.good && !V4L2Request::live && !current->open);
  if(mask)assert(ipe.start({},2)==-EIO);++cases;
 }
 for(unsigned path=0;path<5;path++){
  nextFaults={};CamssIpe ipe("fake",media());assert(!ipe.start({},1));auto input=buffer(1),output=buffer(2);
  Receiver r{&ipe,&input,&output};ipe.processed.connect(&r,&Receiver::ready);assert(!ipe.queue(&input,&output));
  auto *req=ipe.jobs_.at(&output).request;
  if(path==0){ipe.watchdog_.timeout.emit();assert(r.bad==1);}
  if(path==1){r.reenterStop=true;ipe.device_.output()->returnOne();ipe.device_.capture()->returnOne();req->returnOne();assert(!r.good && V4L2Request::live==1);dispatch();assert(r.good==1 && !current->open);}
  if(path==2){current->faults.reinit=true;req->returnOne();assert(!r.bad && current->open);dispatch();assert(r.bad==1 && !current->open);}
  if(path==3){r.requeue=true;req->returnOne();ipe.device_.output()->returnOne();ipe.device_.capture()->returnOne();assert(r.good==1 && ipe.jobs_.size()==1);dispatch();assert(ipe.jobs_.size()==1);ipe.stop();assert(r.bad==1);}
  if(path==4){auto other=buffer(3);assert(ipe.queue(&input,&other)==-EBUSY);assert(ipe.queue(&other,&input)==-ENOBUFS);ipe.stop();assert(r.bad==1);}
  ipe.stop();dispatch();assert(!V4L2Request::live && FrameBuffer::live==2);++cases;
 }
 nextFaults={};nextFaults.legacy=true;{
  CamssIpe ipe("fake",media());assert(!ipe.start({},1));auto input=buffer(1),output=buffer(2);Receiver r{&ipe,&input,&output};ipe.processed.connect(&r,&Receiver::ready);
  qcom_ipe_a5_frame_params packet{};assert(ipe.queue(&input,&output,&packet)==-ENOTSUP);
  assert(!ipe.queue(&input,&output));ipe.device_.output()->returnOne();ipe.device_.capture()->returnOne();assert(r.good==1 && !r.bad);ipe.stop();++cases;
 }
 assert(FrameBuffer::live==0 && V4L2Request::live==0 && deferred.empty());
 std::cout<<"IPE_REQUEST_MODEL cases="<<cases<<" passed=1\n";
}
