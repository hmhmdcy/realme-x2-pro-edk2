/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* A reversible capacity hint for the shared camera manager thread. */
#pragma once
#include <algorithm>
#include <array>
#include <bitset>
#include <cerrno>
#include <cstdint>
#include <fstream>
#include <limits>
#include <memory>
#include <mutex>
#include <new>
#include <optional>
#include <sched.h>
#include <string>
#include <sys/syscall.h>
#include <unistd.h>

namespace libcamera {
using CapacityCpuMask = std::bitset<CPU_SETSIZE>;

class CapacityThreadOps
{
public:
 virtual ~CapacityThreadOps() = default;
 virtual pid_t currentThread() = 0;
 virtual std::optional<CapacityCpuMask> affinity(pid_t tid) = 0;
 virtual int setAffinity(pid_t tid,const CapacityCpuMask &mask) = 0;
 virtual std::optional<unsigned> capacity(unsigned cpu) = 0;
};

class LinuxCapacityThreadOps final : public CapacityThreadOps
{
public:
 pid_t currentThread() override {return syscall(SYS_gettid);}
 std::optional<CapacityCpuMask> affinity(pid_t tid) override
 {
  cpu_set_t native;CPU_ZERO(&native);
  if(sched_getaffinity(tid,sizeof(native),&native))return std::nullopt;
  CapacityCpuMask mask;
  for(unsigned i=0;i<CPU_SETSIZE;++i)if(CPU_ISSET(i,&native))mask.set(i);
  return mask.any()?std::optional<CapacityCpuMask>(mask):std::nullopt;
 }
 int setAffinity(pid_t tid,const CapacityCpuMask &mask) override
 {
  if(mask.none())return -EINVAL;
  cpu_set_t native;CPU_ZERO(&native);
  for(unsigned i=0;i<CPU_SETSIZE;++i)if(mask[i])CPU_SET(i,&native);
  return sched_setaffinity(tid,sizeof(native),&native)?-errno:0;
 }
 std::optional<unsigned> capacity(unsigned cpu) override
 {
  std::ifstream file("/sys/devices/system/cpu/cpu"+std::to_string(cpu)+"/cpu_capacity");
  uint64_t value=0;
  if(!(file>>value) || !value || value>std::numeric_limits<unsigned>::max())return std::nullopt;
  file>>std::ws;if(!file.eof())return std::nullopt;
  return unsigned(value);
 }
};

class ThreadCapacityLease
{
 struct State {
  std::mutex mutex;
  CapacityThreadOps *ops=nullptr;
  pid_t tid=0;unsigned users=0;bool alive=true,revoked=false,pendingRestore=false;
  CapacityCpuMask original,selected;
 };
 /* This guard is destroyed before a normal pthread releases/reuses its TID.
  * Cross-thread release holds the same lock, so it cannot target a reused TID. */
 struct ThreadOwner {
  std::shared_ptr<State> state;
  ~ThreadOwner(){if(state){std::lock_guard lock(state->mutex);state->alive=false;}}
 };
 static ThreadOwner &owner(){static thread_local ThreadOwner value;return value;}
 static CapacityThreadOps &linuxOps(){static LinuxCapacityThreadOps ops;return ops;}
public:
 struct Result {
  int status=0;const char *reason="inactive";pid_t tid=0;unsigned users=0;
  bool active=false;CapacityCpuMask original,selected;
 };
 explicit ThreadCapacityLease(CapacityThreadOps &ops=linuxOps()):ops_(&ops){}
 ~ThreadCapacityLease()
 {
  release();
  if(state_){auto state=state_;std::lock_guard lock(state->mutex);--state->users;state->pendingRestore=true;state_.reset();}
 }
 ThreadCapacityLease(const ThreadCapacityLease &)=delete;
 ThreadCapacityLease &operator=(const ThreadCapacityLease &)=delete;
 ThreadCapacityLease(ThreadCapacityLease &&other):ops_(other.ops_),state_(std::move(other.state_)){}
 ThreadCapacityLease &operator=(ThreadCapacityLease &&)=delete;

 Result acquire()
 {
  if(state_){
   {std::lock_guard lock(state_->mutex);if(state_->alive)return result(*state_,0,"already-held",true);}
   release();
  }
  std::shared_ptr<State> state;
  try {
   auto &thread=owner();if(!thread.state)thread.state=std::make_shared<State>();state=thread.state;
  } catch(const std::bad_alloc &) {Result failed;failed.status=-ENOMEM;failed.reason="no-memory";return failed;}
  std::lock_guard lock(state->mutex);
  if(state->users){
   if(state->ops!=ops_)return result(*state,-EBUSY,"backend-mismatch",false);
   auto current=ops_->affinity(state->tid);
   if(!current)return result(*state,-EIO,"read-failed",false);
   if(state->revoked || *current!=state->selected){state->revoked=true;return result(*state,0,"external-policy",false);}
   ++state->users;state_=state;return result(*state,0,"shared",true);
  }
  if(state->pendingRestore && state->ops==ops_){
   auto current=ops_->affinity(state->tid);
   if(!current)return result(*state,-EIO,"pending-read-failed",false);
   if(*current==state->selected){
    const int status=ops_->setAffinity(state->tid,state->original);
    if(status)return result(*state,status,"restore-pending",false);
   }
  }
  state->pendingRestore=false;
  state->tid=ops_->currentThread();state->ops=ops_;state->revoked=false;
  state->original.reset();state->selected.reset();
  auto original=ops_->affinity(state->tid);
  if(!original)return result(*state,-EIO,"read-failed",false);
  state->original=*original;
  CapacityCpuMask selected;unsigned minimum=std::numeric_limits<unsigned>::max();
  std::array<unsigned,CPU_SETSIZE> capacities{};
  try {
   for(unsigned i=0;i<CPU_SETSIZE;++i)if((*original)[i]){
    auto value=ops_->capacity(i);if(!value)return result(*state,0,"capacity-unavailable",false);
    capacities[i]=*value;minimum=std::min(minimum,*value);
   }
  } catch(const std::bad_alloc &) {return result(*state,-ENOMEM,"no-memory",false);}
  for(unsigned i=0;i<CPU_SETSIZE;++i)if((*original)[i] && capacities[i]>minimum)selected.set(i);
  if(selected.none())return result(*state,0,"homogeneous",false);
  /* Respect a concurrent change during discovery instead of replacing it. */
  auto current=ops_->affinity(state->tid);
  if(!current)return result(*state,-EIO,"read-failed",false);
  if(*current!=*original)return result(*state,0,"external-policy",false);
  const int status=ops_->setAffinity(state->tid,selected);
  if(status)return result(*state,status,"apply-failed",false);
  state->original=*original;state->selected=selected;state->users=1;state_=state;
  auto applied=ops_->affinity(state->tid);
  if(!applied){
   const int rollback=ops_->setAffinity(state->tid,*original);
   if(rollback)return result(*state,rollback,"rollback-pending",true);
   state->users=0;state_.reset();return result(*state,-EIO,"readback-rolled-back",false);
  }
  /* A cpuset/hotplug intersection may have removed CPUs during the syscall. */
  if(applied->none() || (*applied & ~selected).any()){
   state->users=0;state_.reset();return result(*state,0,"external-policy",false);
  }
  state->selected=*applied;return result(*state,0,"selected",true);
 }

 Result release()
 {
  if(!state_)return {};
  auto state=state_;std::lock_guard lock(state->mutex);
  if(!state->alive){--state->users;state_.reset();return result(*state,0,"owner-exited",false);}
  if(state->users>1){--state->users;state_.reset();return result(*state,0,"shared-released",false);}
  if(state->revoked){state->users=0;state_.reset();return result(*state,0,"external-policy",false);}
  auto current=state->ops->affinity(state->tid);
  if(!current)return result(*state,-EIO,"restore-read-failed",true);
  if(*current!=state->selected){state->users=0;state_.reset();return result(*state,0,"external-policy",false);}
  const int status=state->ops->setAffinity(state->tid,state->original);
  if(status)return result(*state,status,"restore-pending",true);
  auto restored=state->ops->affinity(state->tid);
  state->users=0;state_.reset();
  if(!restored)return result(*state,-EIO,"restore-unverified",false);
  return result(*state,0,*restored==state->original?"restored":"restored-constrained",false);
 }

 static std::string maskString(const CapacityCpuMask &mask)
 {
  std::string result;
  for(unsigned i=0;i<CPU_SETSIZE;++i)if(mask[i]){if(!result.empty())result+=',';result+=std::to_string(i);}
  return result.empty()?"none":result;
 }
private:
 static Result result(const State &state,int status,const char *reason,bool active)
 {return {status,reason,state.tid,state.users,active,state.original,state.selected};}
 CapacityThreadOps *ops_;
 std::shared_ptr<State> state_;
};
}
