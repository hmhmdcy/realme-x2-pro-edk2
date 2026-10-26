/* Test-only queue provider: formats become busy after either allocation. */
#include <cassert>
#include <cerrno>
#include <chrono>
#include <deque>
#include <functional>
#include <iostream>
#include <map>
#include <memory>
#include <string>
#include <utility>
#include <vector>

#define LOG_DECLARE_CATEGORY(...)
struct QuietLog { template<class T> QuietLog &operator<<(const T &) { return *this; } };
#define LOG(...) QuietLog{}
namespace libcamera {
class Object {};
template<class... A> class Signal {
public:
 std::vector<std::function<void(A...)>> slots;
 template<class T> void connect(T *target,void(T::*method)(A...)) {slots.emplace_back([=](A... a){(target->*method)(a...);});}
 void emit(A... a) {auto saved=slots;for(auto &slot:saved)slot(a...);}
};
class Timer {
public:
 void start(std::chrono::steady_clock::duration){active=true;}
 void stop(){active=false;}
 bool isRunning()const{return active;}
 Signal<> timeout;bool active=false;
};
struct FrameMetadata {
 enum Status {FrameSuccess,FrameError,FrameCancelled};
 Status status=FrameSuccess;unsigned sequence=71;uint64_t timestamp=998877;
};
class FrameBuffer {
public:
 struct Plane {std::shared_ptr<int> fd;unsigned offset,length;};
 explicit FrameBuffer(std::vector<Plane> planes):planes_(std::move(planes)){++live;}
 ~FrameBuffer(){--live;}
 const std::vector<Plane> &planes() const {return planes_;}
 const FrameMetadata &metadata() const {return metadata_;}
 class Private {
 public:FrameMetadata &metadata(){return owner->metadata_;}FrameBuffer *owner;
 };
 Private *_d(){priv.owner=this;return &priv;}
 static inline unsigned live=0;
private:
 std::vector<Plane> planes_;FrameMetadata metadata_;Private priv;
};
struct V4L2DeviceFormat {
 int fourcc=12;std::pair<int,int> size={640,480};unsigned planesCount=1;
 struct Plane {unsigned bpl=640,size=460800;} planes[1];
 std::string toString()const{return "fake NV12";}
};
struct Faults {int startStep=0,queueSide=-1;unsigned streamOffMask=0;};
struct Backend {
 Faults faults;unsigned step=0;bool open=false,allocated[2]={},streaming[2]={};
 std::deque<FrameBuffer *> queued[2];
 bool fail(){return ++step==unsigned(faults.startStep);}
};
inline Faults nextFaults;inline Backend *current;
class V4L2VideoDevice {
public:
 V4L2VideoDevice(Backend *b,unsigned side):b_(b),side_(side){}
 int setFormat(V4L2DeviceFormat *) {
  assert(b_->open);
  if(b_->allocated[0] || b_->allocated[1])return -EBUSY;
  return b_->fail()?-EINVAL:0;
 }
 int importBuffers(unsigned count){assert(b_->open && count);if(b_->fail())return -ENOMEM;b_->allocated[side_]=true;return 0;}
 int streamOn(){assert(b_->open && b_->allocated[side_]);if(b_->fail())return -EIO;b_->streaming[side_]=true;return 0;}
 int streamOff(){
  if(b_->faults.streamOffMask & (1U<<side_))return -EIO;
  b_->streaming[side_]=false;
  while(!b_->queued[side_].empty())returnOne(FrameMetadata::FrameCancelled);
  return 0;
 }
 int queueBuffer(FrameBuffer *buffer){
  assert(b_->open && b_->streaming[side_]);
  if(int(side_)==b_->faults.queueSide)return -EIO;
  b_->queued[side_].push_back(buffer);return 0;
 }
 void returnOne(FrameMetadata::Status status=FrameMetadata::FrameSuccess){
  assert(!b_->queued[side_].empty());FrameBuffer *buffer=b_->queued[side_].front();b_->queued[side_].pop_front();
  auto &m=buffer->_d()->metadata();m.status=status;m.sequence=2;m.timestamp=123;
  bufferReady.emit(buffer);
 }
 void setDequeueTimeout(std::chrono::steady_clock::duration){}
 Signal<FrameBuffer *> bufferReady;Signal<> dequeueTimeout;
 Backend *b_;unsigned side_;
};
class V4L2M2MDevice {
public:
 explicit V4L2M2MDevice(const std::string &):b{},out(&b,0),cap(&b,1){b.faults=nextFaults;current=&b;}
 int open(){if(b.fail())return -EACCES;b.open=true;return 0;}
 void close(){b.open=false;for(unsigned i=0;i<2;++i){b.allocated[i]=b.streaming[i]=false;b.queued[i].clear();}}
 V4L2VideoDevice *output(){return &out;}V4L2VideoDevice *capture(){return &cap;}
 Backend b;V4L2VideoDevice out,cap;
};
} /* namespace libcamera */
