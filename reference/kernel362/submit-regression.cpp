/* Exercise the verbatim production submission method with recursive proxy callbacks. */
#include <algorithm>
#include <cassert>
#include <cerrno>
#include <cstdint>
#include <deque>
#include <functional>
#include <map>
#include <optional>
#include <sstream>
#include <string>
#include <utility>
#include <vector>
#include <iostream>
#define LOG(...) std::ostringstream()
namespace controls { struct Id { int id() const { return 1; } }; inline Id AwbEnable; }
struct ControlList {
 int value = 0;
 bool contains(int) const { return true; }
 std::optional<bool> get(controls::Id) const { return value != 0; }
};
namespace ipa::camss {
struct AutoIspUpdate { bool valid = false; uint32_t revision = 0; };
struct SensorContext {};
}
struct Buffer {
 struct Plane { uint32_t bytesused = 10; };
 struct Metadata { std::vector<Plane> planes() const { return {{}}; } };
 Metadata metadata() const { return {}; }
};
struct Proxy {
 std::function<int(uint64_t,uint32_t,const ControlList &,ipa::camss::AutoIspUpdate *)> apply;
 std::function<void(uint64_t,uint32_t,uint32_t)> stats;
 int applyIspControls(uint64_t epoch,uint32_t sof,const ControlList &c,ipa::camss::AutoIspUpdate *u) { return apply(epoch,sof,c,u); }
 void processStats(uint64_t epoch,uint32_t sof,uint32_t id,uint32_t,const ipa::camss::SensorContext &) { stats(epoch,sof,id); }
};
struct CamssVfeData {
 struct IspControls { ControlList controls; uint32_t source; };
 struct PendingStats { uint32_t sof; Buffer *buffer; bool submitted; };
 bool running_=true,paramsApplied_=true,parameterBusy_=false,ispHealthy_=true,submittingStatistics_=false;
 uint64_t epoch_=1;
 std::deque<IspControls> ispControls_;
 std::optional<int64_t> imageSequenceOffset_=0;
 std::optional<uint32_t> lastSof_=100;
 std::map<uint32_t,PendingStats> pendingStats_;
 std::map<uint32_t,ipa::camss::SensorContext> sensorContexts_;
 Proxy *ipa_;
 unsigned queued=0;
 void queueIspUpdate(const ipa::camss::AutoIspUpdate &) {
  parameterBusy_=true;++queued;submitStatistics();
 }
 void submitStatistics();
};
#include "method.inc"
int main(int argc,char **argv)
{
 assert(argc==2);const std::string scenario=argv[1];
 CamssVfeData d;Proxy proxy;d.ipa_=&proxy;Buffer buffer;
 unsigned calls=0;std::vector<int> order;
 proxy.apply=[&](uint64_t,uint32_t,const ControlList &c,ipa::camss::AutoIspUpdate *) {
  ++calls;order.push_back(c.value);return 0;
 };
 proxy.stats=[](uint64_t,uint32_t,uint32_t) {};
 d.ispControls_.push_back({{12},12});
 if(scenario=="recursive-control") {
  proxy.apply=[&](uint64_t,uint32_t,const ControlList &,ipa::camss::AutoIspUpdate *) {
   if(++calls==1)d.submitStatistics();return 0;
  };
  d.submitStatistics();assert(calls==1 && d.ispControls_.empty());
 } else if(scenario=="retry-order") {
  proxy.apply=[&](uint64_t,uint32_t,const ControlList &c,ipa::camss::AutoIspUpdate *) {
   order.push_back(c.value);
   if(++calls==1){d.ispControls_.push_back({{13},13});d.submitStatistics();return -EAGAIN;}
   return 0;
  };
  d.submitStatistics();assert(calls==1 && d.ispControls_.size()==2);
  d.submitStatistics();assert((order==std::vector<int>{12,12,13}) && d.ispControls_.empty());
 } else if(scenario=="stop-during-call" || scenario=="restart-during-call") {
  proxy.apply=[&](uint64_t,uint32_t,const ControlList &,ipa::camss::AutoIspUpdate *u) {
   ++calls;d.running_=false;d.ispControls_.clear();u->valid=true;
   if(scenario=="restart-during-call"){++d.epoch_;d.running_=true;d.ispControls_.push_back({{90},90});}
   return scenario=="restart-during-call"?0:-EAGAIN;
  };
  d.submitStatistics();assert(calls==1 && d.queued==0);
  assert(d.ispControls_.size()==(scenario=="restart-during-call"?1U:0U));
  if(!d.ispControls_.empty())assert(d.ispControls_.front().source==90);
 } else if(scenario=="parameter-recursion") {
  d.ispControls_.push_back({{13},13});
  proxy.apply=[&](uint64_t,uint32_t,const ControlList &,ipa::camss::AutoIspUpdate *u) {
   ++calls;d.submitStatistics();u->valid=true;u->revision=1;return 0;
  };
  d.submitStatistics();assert(calls==1 && d.queued==1 && d.ispControls_.size()==1);
 } else if(scenario=="recursive-stats" || scenario=="stop-during-stats") {
  d.ispControls_.clear();d.pendingStats_.emplace(1,CamssVfeData::PendingStats{1,&buffer,false});
  d.pendingStats_.emplace(2,CamssVfeData::PendingStats{2,&buffer,false});
  proxy.stats=[&](uint64_t,uint32_t,uint32_t id) {
   ++calls;order.push_back(id);d.pendingStats_.erase(id);
   if(scenario=="stop-during-stats"){d.running_=false;d.pendingStats_.clear();}
   d.submitStatistics();
  };
  d.submitStatistics();assert(calls==(scenario=="stop-during-stats"?1U:2U));
  assert(d.pendingStats_.empty());
 } else if(scenario=="error-unlocks") {
  proxy.apply=[&](uint64_t,uint32_t,const ControlList &,ipa::camss::AutoIspUpdate *) {++calls;return -EINVAL;};
  d.submitStatistics();assert(calls==1 && !d.ispHealthy_);
 } else return 2;
 assert(!d.submittingStatistics_);
 std::cout<<"PASS "<<scenario<<" calls="<<calls<<std::endl;
}
