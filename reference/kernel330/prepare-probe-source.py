from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel325/lsc-smoke.cpp').read_text()
a=s.index('class Capture {');b=s.index('\nint main(',a)
s=s[:a]+'''class Capture {
public:
 std::shared_ptr<Camera> camera;
 std::mutex mutex;std::condition_variable condition;
 bool running=false,done=false;unsigned frames=0,failed=0,phase=0;
 uint64_t lastTimestamp=0;std::vector<uint8_t> previous;
 std::vector<std::vector<uint8_t>> images;
 std::vector<int> targets;
 void complete(Request *request) {
  std::lock_guard lock(mutex);
  if(!running || done || request->status()==Request::RequestCancelled)return;
  bool next=false;
  const int target=targets[phase];
  auto temperature=request->metadata().get(controls::ColourTemperature);
  auto gains=request->metadata().get(controls::ColourGains);
  const bool applied=target ? temperature==target : !temperature;
  for(const auto &[stream,buffer]:request->buffers()) {
   (void)stream;const auto &m=buffer->metadata();std::vector<uint8_t> data;
   if(m.status!=FrameMetadata::FrameSuccess || !m.timestamp || m.timestamp<=lastTimestamp || !readFrame(buffer,&data))++failed;
   bool settled=applied && gains && m.sequence>=2 && !data.empty() && data==previous;
   if(applied)previous=data;else previous.clear();
   lastTimestamp=m.timestamp;
   std::cout<<"CCT_FRAME sequence="<<m.sequence<<" target="<<target<<" metadata="<<temperature.value_or(0)<<" settled="<<settled;
   if(gains)std::cout<<" red="<<(*gains)[0]<<" blue="<<(*gains)[1];
   std::cout<<std::endl;
   if(settled) {
    images.push_back(std::move(data));
    if(++phase==targets.size())done=true;
    else {next=true;previous.clear();}
   }
  }
  ++frames;done|=failed!=0;
  if(!done) {
   request->reuse(Request::ReuseBuffers);request->controls().clear();
   if(next)request->controls().set(controls::ColourTemperature,targets[phase]);
   if(camera->queueRequest(request)){++failed;done=true;}
  }
  condition.notify_one();
 }
};'''+s[b:]
s=s.replace('if(argc!=7)return 2;','if(argc!=8)return 2;\n int useCct=std::atoi(argv[7]);if(useCct!=0 && useCct!=1)return 2;')
s=s.replace('#include <cstdio>','#include <cstdio>\n#include <cstdlib>')
s=s.replace('Capture capture;for','Capture capture;capture.targets=useCct?std::vector<int>{6500,2850}:std::vector<int>{0};for')
s=s.replace('std::cout<<"LSC_CONFIG stride="', '''bool supported=camera->controls().find(&controls::ColourTemperature)!=camera->controls().end();
 if(supported!=bool(useCct))return 5;
 std::cout<<"CCT_CONTROL supported="<<supported<<std::endl;
 std::cout<<"LSC_CONFIG stride="''')
s=s.replace('const std::array<float,2> gains{1,1};initial.set(controls::ColourGains,Span<const float,2>(gains));',
 '''if(useCct)initial.set(controls::ColourTemperature,6500);
 else {const std::array<float,2> gains{1,1};initial.set(controls::ColourGains,Span<const float,2>(gains));}''')
a=s.index(' bool good=!stopped');b=s.index(' return good?0:9;',a)
s=s[:a]+''' bool good=!stopped && !capture.failed && capture.done && capture.images.size()==capture.targets.size();
 if(good)for(size_t i=0;i<capture.images.size();++i) {
  const auto &data=capture.images[i];
  std::string path=std::string(argv[3])+"-"+std::to_string(capture.targets[i])+"-private.nv12";
  int out=open(path.c_str(),O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC,0600);
  if(out<0){good=false;break;}
  size_t written=0;while(written<data.size()){ssize_t n=write(out,data.data()+written,data.size()-written);if(n<=0){good=false;break;}written+=n;}
  if(close(out))good=false;
 }
 std::cout<<"CCT_RESULT frames="<<capture.frames<<" phases="<<capture.images.size()<<" failed="<<!good<<" result="<<!good<<std::endl;
'''+s[b:]
(HERE/'cct-smoke.cpp').write_text(s)
print('Prepared startup6500→runtime2850 public-control probe and legacy unity mode.')
