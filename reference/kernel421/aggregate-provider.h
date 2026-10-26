/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "ipe_frame_history.h"
#include <algorithm>
#include <cassert>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <map>
#include <queue>
#include <vector>
using libcamera::ipa::camss::IpeFrameHistory;
using libcamera::ipa::camss::IpeFrameObservation;
struct NullLog {template<typename T> NullLog &operator<<(const T&){return *this;}};
#define LOG(...) NullLog()
struct FrameMetadata {enum Status{FrameSuccess,FrameError};Status status=FrameSuccess;};
struct FrameBuffer {uint32_t sof=0;FrameMetadata meta;FrameBuffer *_d(){return this;}uint32_t kernelSequence(){return sof;}FrameMetadata &metadata(){return meta;}};
struct Request {uint32_t id=0;uint32_t sequence(){return id;}};
struct Timer {bool active=false;bool isRunning(){return active;}template<typename T>void start(T){active=true;}void stop(){active=false;}};
struct FakeIpa {IpeFrameHistory history;std::vector<int> receipts;void frameProcessed(uint64_t epoch,uint32_t sof,uint64_t token,bool success){receipts.push_back(history.resolve(epoch,sof,token,success));}};
struct FakeHandler {unsigned buffers=0,requests=0;void completeBuffer(Request*,FrameBuffer*){++buffers;}void completeRequest(Request*){++requests;}};
class CamssVfeData {
public:
 struct PendingFrame {FrameBuffer *image=nullptr,*raw=nullptr,*ifeImage=nullptr;bool imageFinished=false,rawReady=false,failed=false;uint64_t ipeToken=0;uint32_t ipeSof=0;};
 std::map<Request*,PendingFrame> requests_;
 std::map<FrameBuffer*,Request*> internalRequests_;
 std::queue<FrameBuffer*> freeImages_;
 std::map<uint32_t,uint64_t> pixStarts_,rawStarts_;
 std::map<uint32_t,FrameBuffer*> images_;
 bool rawEnabled_=true,running_=true,processedEnabled_=true;
 void *ipe_=this;uint64_t epoch_=1,framePeriod_=33333333;Timer deadline_;
 FakeIpa object;FakeIpa *ipa_=&object;FakeHandler callbacks;
 FakeHandler *handler(){return &callbacks;}
 void tryComplete(Request *request,bool timeout=false);
 uint64_t add(Request *request,FrameBuffer *image,FrameBuffer *raw,FrameBuffer *ife)
 {
  IpeFrameObservation f;f.epoch=epoch_;f.sof=ife->sof;f.exposureNs=100;f.exposureLines=1;f.analogueGain=1;f.population=1;f.histogram[0]=1;
  uint64_t token;assert(!object.history.prepare(f,&token));requests_[request]={image,raw,ife,true,true,false,token,ife->sof};internalRequests_[ife]=request;
  pixStarts_[ife->sof]=rawStarts_[raw->sof]=100000000;return token;
 }
 CamssVfeData(){assert(object.history.start(epoch_));}
};
