using namespace libcamera;
struct Receiver {
 CamssIpe *ipe;FrameBuffer *input,*output;unsigned good=0,bad=0;bool requireClosed=false,reenterStop=false;
 void ready(FrameBuffer *a,FrameBuffer *b,bool success){
  assert(a==input && b==output);
  assert(input->metadata().sequence==71 && input->metadata().timestamp==998877);
  if(requireClosed)assert(!current->open);
  if(success)++good;else ++bad;
  if(reenterStop)ipe->stop();
 }
};
int main(){
 unsigned cases=0;
 for(int fail=1;fail<=7;++fail){
  nextFaults={fail,-1,0};CamssIpe ipe("fake");assert(ipe.start({},4)<0);assert(!current->open);ipe.stop();++cases;
 }
 for(unsigned order=0;order<2;++order){
  nextFaults={};CamssIpe ipe("fake");assert(!ipe.start({},4));
  FrameBuffer input({{std::make_shared<int>(1),0,460800}}),output({{std::make_shared<int>(2),0,460800}});
  Receiver receiver{&ipe,&input,&output};ipe.processed.connect(&receiver,&Receiver::ready);
  assert(!ipe.queue(&input,&output));assert(FrameBuffer::live==3 && ipe.watchdog_.isRunning());
  (order?ipe.device_.capture():ipe.device_.output())->returnOne();assert(receiver.good==0 && FrameBuffer::live==3 && ipe.watchdog_.isRunning());
  (order?ipe.device_.output():ipe.device_.capture())->returnOne();assert(receiver.good==1 && !receiver.bad && FrameBuffer::live==2 && !ipe.watchdog_.isRunning());
  assert(ipe.jobs_.empty() && ipe.inputs_.empty());ipe.stop();++cases;
 }
 for(int side=0;side<2;++side){
  nextFaults={0,side,0};CamssIpe ipe("fake");assert(!ipe.start({},4));
  FrameBuffer input({{std::make_shared<int>(1),0,460800}}),output({{std::make_shared<int>(2),0,460800}});
  Receiver receiver{&ipe,&input,&output,0,0,true};ipe.processed.connect(&receiver,&Receiver::ready);
  assert(!ipe.queue(&input,&output));assert(receiver.bad==1 && !receiver.good && FrameBuffer::live==2);
  assert(ipe.queue(&input,&output)==-EPIPE);ipe.stop();assert(receiver.bad==1);++cases;
 }
 for(unsigned mask=0;mask<4;++mask){
  nextFaults={0,-1,mask};CamssIpe ipe("fake");assert(!ipe.start({},4));
  FrameBuffer input({{std::make_shared<int>(1),0,460800}}),output({{std::make_shared<int>(2),0,460800}});
  Receiver receiver{&ipe,&input,&output,0,0,mask!=0};ipe.processed.connect(&receiver,&Receiver::ready);
  assert(!ipe.queue(&input,&output));ipe.stop();assert(receiver.bad==1 && !receiver.good && FrameBuffer::live==2 && !current->open && !ipe.watchdog_.isRunning());
  if(mask)assert(ipe.start({},4)==-EIO);
  else {assert(!ipe.start({},4));ipe.stop();}
  ++cases;
 }
 for(unsigned path=0;path<3;++path){
  nextFaults={};CamssIpe ipe("fake");assert(!ipe.start({},4));
  FrameBuffer input({{std::make_shared<int>(1),0,460800}}),output({{std::make_shared<int>(2),0,460800}});
  Receiver receiver{&ipe,&input,&output};ipe.processed.connect(&receiver,&Receiver::ready);
  assert(!ipe.queue(&input,&output));
  if(path==0){ipe.watchdog_.timeout.emit();assert(receiver.bad==1 && !ipe.watchdog_.isRunning());}
  if(path==1){receiver.reenterStop=true;ipe.device_.capture()->returnOne();ipe.device_.output()->returnOne();assert(receiver.good==1 && !current->open);}
  if(path==2){ipe.device_.output()->returnOne(FrameMetadata::FrameError);assert(!receiver.bad);ipe.device_.capture()->returnOne();assert(receiver.bad==1);}
  assert(FrameBuffer::live==2);ipe.stop();++cases;
 }
 assert(FrameBuffer::live==0);
 std::cout<<"IPE_MODEL cases="<<cases<<" passed=1\n";
}
