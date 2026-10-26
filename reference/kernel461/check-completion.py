"""ASAN/UBSAN checks of the actual full completion function and actual stop drain."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel461')


def function(source):
    begin=source.index('void CamssVfeData::tryComplete(Request *request,bool timeout)')
    end=source.index('\nvoid CamssVfeData::paramsReady(',begin)
    return source[begin:end].replace('void CamssVfeData::tryComplete(', 'void Fixture::tryComplete(',1)


def main():
    baseline=(PRIVATE/'camss_vfe-baseline.cpp').read_text()
    fixed=(PRIVATE/'camss_vfe-candidate.cpp').read_text()
    start=baseline.index(' while (!d->requests_.empty()) {')
    end=baseline.index('\n d->histograms_.clear();',start)
    drain=baseline[start:end].replace('d->','')
    harness=r'''
#include <algorithm>
#include <array>
#include <cassert>
#include <chrono>
#include <cstdint>
#include <functional>
#include <iostream>
#include <map>
#include <memory>
#include <optional>
#include <queue>
#include <set>
#include <string>
#include <vector>
struct Sink { template<class T> Sink &operator<<(const T &) { return *this; } };
#define LOG(...) Sink{}
struct FrameMetadata { enum Status { FrameSuccess, FrameError, FrameCancelled }; Status status=FrameSuccess; uint64_t timestamp=100; };
struct FrameBuffer {
 struct Private { FrameMetadata value; uint32_t sof=11; FrameMetadata &metadata(){return value;} uint32_t kernelSequence()const{return sof;} } private_;
 const FrameMetadata &metadata()const{return private_.value;} Private *_d(){return &private_;}
};
struct Request { uint32_t serial=1; uint32_t sequence()const{return serial;} };
namespace camss_diag { enum class EventType { InternalReturn, RequestComplete }; constexpr uint32_t Unknown=UINT32_MAX; }
struct Fixture {
 struct PendingFrame {
  FrameBuffer *image=nullptr,*raw=nullptr,*ifeImage=nullptr,*coarse=nullptr;
  bool imageFinished=true,rawReady=true,failed=false;
  uint64_t ipeToken=71;uint32_t ipeSof=11;
  std::optional<std::array<float,9>> ipeColourMatrix{};
#ifndef BASELINE
  bool ipaCompleting=false;
#endif
 };
 struct Proxy {
  struct Receipt { uint64_t epoch;uint32_t sof;uint64_t token;bool success; };
  std::vector<Receipt> receipts;std::function<void()> hook;
  void frameProcessed(uint64_t epoch,uint32_t sof,uint64_t token,bool success) {
   receipts.push_back({epoch,sof,token,success});
   if(hook){auto next=std::move(hook);hook={};next();}
  }
 } proxy;
 struct Handler {
  Fixture *f;
  void completeBuffer(Request *r,FrameBuffer *b) {
   f->bufferCompletions[r].push_back(b->metadata().status);
  }
  void completeRequest(Request *r) {
   assert(f->corePending.erase(r)==1);++f->requestCompletions[r];
  }
 } pipe{this};
 struct Timer {bool active=false;bool isRunning(){return active;}template<class T>void start(T){active=true;}void stop(){active=false;}}deadline_;
 bool rawEnabled_=false,running_=true,processedEnabled_=true;
 uint64_t epoch_=1,framePeriod_=33333333;
 int *ipe_=reinterpret_cast<int*>(uintptr_t(1));Proxy *ipa_=&proxy;
 Request *ipeActive_=nullptr;
 std::map<Request*,PendingFrame>requests_;
 std::map<FrameBuffer*,Request*>internalRequests_;
 std::queue<FrameBuffer*>freeImages_;
 std::map<uint32_t,FrameBuffer*>images_;
 std::map<uint32_t,int>histograms_;
 std::map<uint32_t,uint64_t>pixStarts_,rawStarts_;
 std::vector<std::unique_ptr<FrameBuffer>>pool;
 std::map<Request*,std::vector<FrameMetadata::Status>>bufferCompletions;
 std::map<Request*,unsigned>requestCompletions;
 std::set<Request*>corePending;
 unsigned finished=0,missing=0;bool stopDrainedCore=false;
 Handler *handler(){return &pipe;}
 void traceFull(camss_diag::EventType,Request*,FrameBuffer*,uint32_t=0,uint64_t=0,int32_t=0){}
 void finish(uint32_t,bool){++finished;}
 void completeMissingStatistics(){++missing;}
 void tryComplete(Request*,bool=false);
 FrameBuffer *newBuffer(){pool.emplace_back(std::make_unique<FrameBuffer>());return pool.back().get();}
 void add(Request *r) {
  auto *input=newBuffer();auto *output=newBuffer();
  PendingFrame frame;frame.ifeImage=input;frame.image=output;
  requests_.emplace(r,frame);internalRequests_[input]=r;ipeActive_=r;corePending.insert(r);
 }
 void stop() {
  running_=false;
@@DRAIN@@
  stopDrainedCore=corePending.empty();
  internalRequests_.clear();freeImages_={};pool.clear();
 }
};
@@FUNCTION@@
int main(int argc,char **argv) {
 assert(argc==2);const std::string name=argv[1];Fixture f;Request request;f.add(&request);
 if(name=="normal") {
  f.tryComplete(&request);assert(f.proxy.receipts.size()==1 && f.proxy.receipts[0].success);
  assert(f.requestCompletions[&request]==1 && f.freeImages_.size()==1 && f.requests_.empty());
  assert(f.bufferCompletions[&request]==std::vector<FrameMetadata::Status>{FrameMetadata::FrameSuccess});
 } else if(name=="stop") {
  f.proxy.hook=[&]{f.stop();};f.tryComplete(&request);
  assert(f.stopDrainedCore && f.requestCompletions[&request]==1 && f.requests_.empty());
  assert(f.bufferCompletions[&request]==std::vector<FrameMetadata::Status>{FrameMetadata::FrameCancelled});
  assert(f.proxy.receipts.size()==1 && !f.ipeActive_ && f.freeImages_.empty());
 } else if(name=="epoch") {
  Request next;next.serial=20;
  f.proxy.hook=[&]{f.stop();++f.epoch_;f.running_=true;f.add(&next);};
  f.tryComplete(&request);assert(f.stopDrainedCore && f.requestCompletions[&request]==1);
  assert(f.requests_.size()==1 && f.requests_.count(&next) && f.ipeActive_==&next);
  assert(!f.requestCompletions[&next] && f.proxy.receipts.size()==1);
 } else if(name=="reused-request") {
  f.proxy.hook=[&]{f.stop();++f.epoch_;f.running_=true;++request.serial;f.add(&request);};
  f.tryComplete(&request);assert(f.requestCompletions[&request]==1 && f.requests_.size()==1);
  assert(f.requests_.count(&request) && f.ipeActive_==&request && f.proxy.receipts.size()==1);
 } else if(name=="nested") {
  f.proxy.hook=[&]{f.tryComplete(&request);};f.tryComplete(&request);
  assert(f.proxy.receipts.size()==1 && f.requestCompletions[&request]==1 && f.requests_.empty());
 } else if(name=="nested-timeout") {
  f.proxy.hook=[&]{f.tryComplete(&request,true);};f.tryComplete(&request);
  assert(f.proxy.receipts.size()==1 && f.requestCompletions[&request]==1);
  assert(f.bufferCompletions[&request]==std::vector<FrameMetadata::Status>{FrameMetadata::FrameSuccess});
 } else if(name=="failure") {
  f.requests_.at(&request).failed=true;f.tryComplete(&request);
  assert(f.proxy.receipts.size()==1 && !f.proxy.receipts[0].success);
  assert(f.bufferCompletions[&request]==std::vector<FrameMetadata::Status>{FrameMetadata::FrameError});
 } else if(name=="zero-token") {
  f.requests_.at(&request).ipeToken=0;f.tryComplete(&request);
  assert(f.proxy.receipts.empty() && f.requestCompletions[&request]==1 && f.requests_.empty());
 } else if(name=="raw-wait") {
  f.rawEnabled_=true;auto &frame=f.requests_.at(&request);frame.raw=f.newBuffer();frame.rawReady=false;
  f.tryComplete(&request);assert(f.proxy.receipts.empty() && f.requests_.size()==1);
  frame.rawReady=true;f.tryComplete(&request);assert(f.proxy.receipts.empty() && f.requests_.size()==1);
  f.tryComplete(&request,true);assert(f.proxy.receipts.size()==1 && !f.proxy.receipts[0].success);
  assert(f.requestCompletions[&request]==1 && f.bufferCompletions[&request].size()==2);
 } else if(name=="stopped-entry") {
  f.stop();assert(f.proxy.receipts.size()==1 && !f.proxy.receipts[0].success);
  assert(f.stopDrainedCore && f.requestCompletions[&request]==1);
 } else return 2;
 std::cout<<name<<" passed\n";
}
'''
    cases=['normal','stop','epoch','reused-request','nested','nested-timeout','failure','zero-token','raw-wait','stopped-entry']
    results=[]
    for variant,source,defines in [('baseline',baseline,['-DBASELINE']),('fixed',fixed,[])]:
        cpp=PRIVATE/('completion-'+variant+'.cpp');binary=PRIVATE/('completion-'+variant)
        body=harness.replace('@@DRAIN@@',drain).replace('@@FUNCTION@@',function(source))
        cpp.write_text(body)
        command=['g++','-std=c++20','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
                 '-fno-omit-frame-pointer',*defines,str(cpp),'-o',str(binary)]
        run=subprocess.run(command,capture_output=True)
        (PRIVATE/('completion-'+variant+'-compile-private.log')).write_bytes(run.stdout+run.stderr)
        assert run.returncode==0,(run.stdout+run.stderr).decode()
        chosen=['normal','stop'] if variant=='baseline' else cases
        for case in chosen:
            run=subprocess.run([str(binary),case],capture_output=True,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=1:halt_on_error=1'))
            output=run.stdout+run.stderr
            (PRIVATE/f'completion-{variant}-{case}-private.log').write_bytes(output)
            expected=variant=='baseline' and case=='stop'
            if expected:
                assert run.returncode!=0 and b'heap-use-after-free' in output,output.decode()
            else:assert run.returncode==0,output.decode()
            results.append(dict(variant=variant,case=case,exit_code=run.returncode,
                                expected_baseline_uaf=expected,passed=True))
    report=dict(stage=461,actual_full_tryComplete_function_extracted=True,actual_stop_request_drain_extracted=True,
                baseline452_stop_reentry_uaf_reproduced=True,host_asan_ubsan=True,
                fixed_cases=len(cases),cases=results,
                normal_history_receipt_then_ownership_return_and_completion_preserved=True,
                stop_cancellation_once_and_core_pending_drained=True,
                nested_ready_and_timeout_no_duplicate_receipt=True,
                restart_and_reused_request_epoch_guarded=True,
                baseline_function_sha256=hashlib.sha256(function(baseline).encode()).hexdigest(),
                candidate_function_sha256=hashlib.sha256(function(fixed).encode()).hexdigest(),
                candidate_pipeline_sha256=hashlib.sha256(fixed.encode()).hexdigest(),
                phone_sdk_library_build_accessed=False,gap_root_cause_or_frame_rate_fix_proven=False,passed=True)
    (HERE/'completion-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':main()
