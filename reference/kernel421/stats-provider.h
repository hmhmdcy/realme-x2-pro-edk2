/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <deque>
#include <map>
#include <memory>
#include <optional>
#include <vector>
#include <cmath>
#include <iomanip>
#include <linux/videodev2.h>
struct NullLog {template<typename T>NullLog &operator<<(const T&){return *this;}};
#define LOG(...) NullLog()
struct ControlList {};
struct Value {int32_t v;template<typename T>T get()const{return T(v);}};
struct Range {Value min()const{return {1};}Value max()const{return {10000};}};
struct Sensor {std::map<uint32_t,Range> controls()const{return {{V4L2_CID_EXPOSURE,{}},{V4L2_CID_ANALOGUE_GAIN,{}}};}};
struct SensorContext {bool valid=true;uint32_t exposureLines=1,gainCode=1,source=1;};
struct FrameMetadata {enum{FrameSuccess};int status;uint32_t sequence;uint64_t timestamp;struct Plane{uint32_t bytesused;};std::array<Plane,1> plane;auto &planes(){return plane;}};
struct FrameBuffer {FrameMetadata m;FrameBuffer *_d(){return this;}FrameMetadata &metadata(){return m;}uint32_t cookie(){return 1;}};
struct Queue {unsigned queued=0;int queueBuffer(FrameBuffer*){++queued;return 0;}};
namespace ipa::camss {
struct AutoIspUpdate {bool valid=true;uint32_t revision=1;double red=1,blue=1;};
struct AutomaticUpdate {bool valid=false;uint32_t revision=1,exposureLines=1,gainCode=1;};
struct Statistics {int status=0;bool parametersKnown=true,sensorControlsKnown=true;AutomaticUpdate automaticUpdate;AutoIspUpdate ispUpdate;uint32_t ispRevision=0;uint64_t population=100,weightedSum=1,ipeToken=1,ipeHistogramTrace=1,exposureNs=1;float analogueGain=1;};
}
class CamssVfeData;
struct FakeIpa {CamssVfeData *data;bool stopDuringPrepare=false;unsigned prepares=0;int prepareParameters(uint64_t,uint32_t,uint32_t,uint32_t *);void frameProcessed(uint64_t,uint32_t,uint64_t,bool){}};
class CamssVfeData {
public:
 bool running_=true,automatic_=false,sensorContextHealthy_=true,delayedControls_=true,ispHealthy_=true,parameterBusy_=false;
 uint64_t epoch_=1;Sensor object;Sensor *sensor_=&object;std::optional<uint32_t> lastSof_=1;
 std::map<uint32_t,SensorContext> sensorContexts_{{1,{}}};std::optional<ipa::camss::AutomaticUpdate> automaticUpdate_;uint32_t lastAutoRevision_=0;
 struct PendingStats{uint32_t sof;FrameBuffer *buffer;bool submitted;};std::map<uint32_t,PendingStats> pendingStats_;
 struct Histogram{uint64_t population,weightedSum,ipeToken,ipeTrace,exposureNs;float analogueGain;ControlList metadata;};
 std::map<uint32_t,Histogram> histograms_;std::deque<uint32_t> histogramOrder_;std::map<uint32_t,bool> images_{{1,true}};
 struct Size{uint32_t width=20,height=20;}input_;
 Queue statsObject,paramsObject;Queue *stats_=&statsObject,*params_=&paramsObject;
 std::vector<std::unique_ptr<FrameBuffer>> paramsBuffers_;
 FakeIpa ipaObject{this};FakeIpa *ipa_=&ipaObject;uint32_t lastIspRevision_=0,parameterRevision_=0;
 unsigned paired=0,fallback=0,nested=0,submissions=0;bool stopOnFinish=false;
 void finish(uint32_t sof,bool hasHistogram){if(hasHistogram){assert(histograms_.count(sof));++paired;histograms_.erase(sof);}else ++fallback;images_.erase(sof);if(stopOnFinish){running_=false;paramsBuffers_.clear();}}
 void completeMissing(){++nested;std::vector<uint32_t> missing;for(auto [sof,x]:images_){(void)x;bool pending=false;for(auto [id,p]:pendingStats_){(void)id;pending|=p.sof==sof;}if(!histograms_.count(sof)&&!pending)missing.push_back(sof);}for(auto sof:missing)finish(sof,false);}
 void submitStatistics(){++submissions;}
 void queueIspUpdate(const ipa::camss::AutoIspUpdate &update);
 void statsProcessed(uint64_t epoch,uint32_t sof,uint32_t id,const ipa::camss::Statistics &statistics,const ControlList &metadata);
 CamssVfeData(){paramsBuffers_.push_back(std::make_unique<FrameBuffer>());}
};
int FakeIpa::prepareParameters(uint64_t,uint32_t,uint32_t,uint32_t *used){++prepares;*used=32;data->completeMissing();if(stopDuringPrepare){data->running_=false;data->paramsBuffers_.clear();}return 0;}
