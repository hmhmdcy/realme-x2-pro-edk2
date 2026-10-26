/* Deterministic providers for the actual wrapper, not a kernel simulator. */
#include <algorithm>
#include <cassert>
#include <cerrno>
#include <chrono>
#include <cstdint>
#include <deque>
#include <functional>
#include <iostream>
#include <map>
#include <memory>
#include <string>
#include <utility>
#include <vector>
#include <linux/videodev2.h>
#include <linux/qcom-ipe-a5.h>

#define LOG_DECLARE_CATEGORY(...)
struct QuietLog { template<class T> QuietLog &operator<<(const T &) { return *this; } };
#define LOG(...) QuietLog{}
namespace libcamera {
enum ConnectionType { ConnectionTypeQueued };
inline std::deque<std::function<void()>> deferred;
inline void dispatch(){while(!deferred.empty()){auto call=std::move(deferred.front());deferred.pop_front();call();}}
class Object {
public:
 template<class T,class... A> bool invokeMethod(void(T::*method)(A...),ConnectionType type,A... args){
  assert(type==ConnectionTypeQueued);deferred.push_back([=,this]{(static_cast<T *>(this)->*method)(args...);});return true;
 }
};
template<class... A> class Signal {
public:
 std::vector<std::function<void(A...)>> slots;
 template<class T> void connect(T *target,void(T::*method)(A...)){slots.emplace_back([=](A... a){(target->*method)(a...);});}
 void emit(A... a){auto saved=slots;for(auto &slot:saved)slot(a...);}
};
class Timer {
public:
 void start(std::chrono::steady_clock::duration){active=true;}
 void stop(){active=false;}
 bool isRunning()const{return active;}
 Signal<> timeout;bool active=false;
};
template<class T> class Span {
public:
 Span(T *p,size_t n):p_(p),n_(n){} T *data()const{return p_;}size_t size()const{return n_;}
 T *p_;size_t n_;
};
class ControlValue {
public:
 void set(Span<const uint8_t> bytes){data.assign(bytes.data(),bytes.data()+bytes.size());}
 std::vector<uint8_t> data;
};
class ControlList {
public:
 explicit ControlList(int){}
 void set(unsigned id,const ControlValue &value){assert(id==V4L2_CID_QCOM_IPE_A5_FRAME_PARAMS);data=value.data;}
 std::vector<uint8_t> data;
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
 const std::vector<Plane> &planes()const{return planes_;}
 const FrameMetadata &metadata()const{return metadata_;}
 class Private {public:FrameMetadata &metadata(){return owner->metadata_;}FrameBuffer *owner;};
 Private *_d(){priv.owner=this;return &priv;}
 static inline unsigned live=0;
private:
 std::vector<Plane> planes_;FrameMetadata metadata_;Private priv;
};
struct V4L2DeviceFormat {
 int fourcc=12;std::pair<int,int> size={640,480};unsigned planesCount=1;
 struct Plane {unsigned bpl=640,size=460800;}planes[1];
 std::string toString()const{return "fake NV12";}
};
struct Faults {
 int startStep=0,queueSide=-1;unsigned streamOffMask=0;
 bool legacy=false,badShape=false,noMediaRequests=false,allocate=false,controls=false,requestQueue=false,reinit=false;
};
struct Backend {
 Faults faults;unsigned step=0;bool open=false,allocated[2]={},streaming[2]={};
 std::deque<FrameBuffer *> queued[2];
 std::vector<std::vector<uint8_t>> packets;
 bool fail(){return ++step==unsigned(faults.startStep);}
};
inline Faults nextFaults;inline Backend *current;
class V4L2Request {
public:
 explicit V4L2Request(Backend *b):backend(b){++live;}
 ~V4L2Request(){assert(!inCallback);assert(!queued || !backend->open);--live;}
 int reinit(){notifier=false;if(backend->faults.reinit)return -EIO;queued=false;payload.clear();return 0;}
 int queue(){assert(!payload.empty());if(backend->faults.requestQueue)return -EIO;queued=notifier=true;return 0;}
 void returnOne(){assert(queued && notifier);inCallback=true;requestDone.emit(this);inCallback=false;}
 Signal<V4L2Request *> requestDone;
 Backend *backend;std::vector<uint8_t> payload;bool queued=false,notifier=false,inCallback=false;
 static inline unsigned live=0;
};
class MediaDevice {
public:
 bool supportsRequests(){return !current->faults.noMediaRequests;}
 int allocateRequests(unsigned count,std::vector<std::unique_ptr<V4L2Request>> *requests){
  if(current->faults.allocate)return -ENOMEM;
  for(unsigned i=0;i<count;i++)requests->push_back(std::make_unique<V4L2Request>(current));return 0;
 }
};
class V4L2VideoDevice {
public:
 V4L2VideoDevice(Backend *b,unsigned side):b_(b),side_(side){}
 const v4l2_query_ext_ctrl *controlInfo(unsigned id){
  assert(id==V4L2_CID_QCOM_IPE_A5_FRAME_PARAMS);
  if(b_->faults.legacy)return nullptr;
  info={};info.type=V4L2_CTRL_TYPE_U8;info.elem_size=1;info.elems=sizeof(qcom_ipe_a5_frame_params);
  info.nr_of_dims=1;info.dims[0]=b_->faults.badShape?4:info.elems;return &info;
 }
 int controls()const{return 0;}
 int setControls(ControlList *controls,const V4L2Request *request){
  assert(request && side_==0);
  if(b_->faults.controls)return -EIO;
  const_cast<V4L2Request *>(request)->payload=controls->data;b_->packets.push_back(controls->data);return 0;
 }
 int setFormat(V4L2DeviceFormat *){assert(b_->open);if(b_->allocated[0] || b_->allocated[1])return -EBUSY;return b_->fail()?-EINVAL:0;}
 int importBuffers(unsigned count){assert(b_->open && count);if(b_->fail())return -ENOMEM;b_->allocated[side_]=true;return 0;}
 int streamOn(){assert(b_->open && b_->allocated[side_]);if(b_->fail())return -EIO;b_->streaming[side_]=true;return 0;}
 int streamOff(){if(b_->faults.streamOffMask&(1U<<side_))return -EIO;b_->streaming[side_]=false;while(!b_->queued[side_].empty())returnOne(FrameMetadata::FrameCancelled);return 0;}
 int queueBuffer(FrameBuffer *buffer,const V4L2Request *request=nullptr){
  assert(b_->open && b_->streaming[side_]);assert(side_==0 || !request);
  if(!b_->faults.legacy && side_==0)assert(request);
  if(int(side_)==b_->faults.queueSide)return -EIO;b_->queued[side_].push_back(buffer);return 0;
 }
 void returnOne(FrameMetadata::Status status=FrameMetadata::FrameSuccess){
  assert(!b_->queued[side_].empty());FrameBuffer *buffer=b_->queued[side_].front();b_->queued[side_].pop_front();
  auto &m=buffer->_d()->metadata();m.status=status;m.sequence=2;m.timestamp=123;bufferReady.emit(buffer);
 }
 Signal<FrameBuffer *> bufferReady;Backend *b_;unsigned side_;v4l2_query_ext_ctrl info{};
};
class V4L2M2MDevice {
public:
 explicit V4L2M2MDevice(const std::string &):b{},out(&b,0),cap(&b,1){b.faults=nextFaults;current=&b;}
 int open(){if(b.fail())return -EACCES;b.open=true;return 0;}
 void close(){b.open=false;for(unsigned i=0;i<2;i++){b.allocated[i]=b.streaming[i]=false;b.queued[i].clear();}}
 V4L2VideoDevice *output(){return &out;}V4L2VideoDevice *capture(){return &cap;}
 Backend b;V4L2VideoDevice out,cap;
};
} /* namespace libcamera */
