/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "thread_capacity.h"
#include <cassert>
#include <future>
#include <iostream>
#include <map>
#include <thread>
using namespace libcamera;
static CapacityCpuMask mask(std::initializer_list<unsigned> cpus){CapacityCpuMask m;for(auto c:cpus)m.set(c);return m;}
struct Fake final : CapacityThreadOps {
 CapacityCpuMask current=mask({1,5,9});std::map<unsigned,unsigned> caps{{1,200},{5,600},{9,900}};
 unsigned gets=0,sets=0;std::map<unsigned,int> getErrors,setErrors;bool changeSecondGet=false,clip=false;
 pid_t lastTarget=0;
 pid_t currentThread() override{return syscall(SYS_gettid);}
 std::optional<CapacityCpuMask> affinity(pid_t tid) override{
  lastTarget=tid;++gets;if(changeSecondGet && gets==2)current=mask({1});
  if(getErrors.count(gets))return std::nullopt;
  return current;
 }
 int setAffinity(pid_t tid,const CapacityCpuMask &m) override{
  lastTarget=tid;++sets;if(setErrors.count(sets))return setErrors.at(sets);current=clip?(m&mask({9})):m;return 0;
 }
 std::optional<unsigned> capacity(unsigned c) override{auto i=caps.find(c);return i==caps.end()?std::nullopt:std::optional<unsigned>(i->second);}
};
static bool reason(const ThreadCapacityLease::Result &r,const char *s){return std::string(r.reason)==s;}
int main()
{
 unsigned cases=0;const auto original=mask({1,5,9}),selected=mask({5,9});
 {Fake f;ThreadCapacityLease a(f);auto r=a.acquire();assert(r.active&&r.users==1&&f.current==selected);assert(a.acquire().users==1);assert(reason(a.release(),"restored")&&f.current==original);++cases;}
 {Fake f;ThreadCapacityLease a(f),b(f);a.acquire();assert(reason(b.acquire(),"shared"));assert(a.release().users==1&&f.current==selected);assert(reason(b.release(),"restored")&&f.current==original);++cases;}
 {Fake f;f.current=selected;f.caps[5]=900;ThreadCapacityLease a(f);assert(reason(a.acquire(),"homogeneous")&&f.sets==0&&f.current==selected);++cases;}
 {Fake f;f.caps.erase(9);ThreadCapacityLease a(f);assert(reason(a.acquire(),"capacity-unavailable")&&f.sets==0);++cases;}
 {Fake f;f.getErrors[1]=-EIO;ThreadCapacityLease a(f);assert(a.acquire().status==-EIO&&f.current==original);++cases;}
 {Fake f;f.setErrors[1]=-EPERM;ThreadCapacityLease a(f);assert(a.acquire().status==-EPERM&&f.current==original);++cases;}
 {Fake f;f.changeSecondGet=true;ThreadCapacityLease a(f);assert(reason(a.acquire(),"external-policy")&&f.sets==0&&f.current==mask({1}));++cases;}
 {Fake f;ThreadCapacityLease a(f),b(f);a.acquire();f.current=mask({1});assert(reason(b.acquire(),"external-policy"));f.current=selected;assert(reason(a.release(),"external-policy")&&f.current==selected);++cases;}
 {Fake f;ThreadCapacityLease a(f);a.acquire();f.current=mask({1});assert(reason(a.release(),"external-policy")&&f.current==mask({1}));++cases;}
 {Fake f;f.getErrors[3]=-EIO;ThreadCapacityLease a(f);auto r=a.acquire();assert(!r.active&&reason(r,"readback-rolled-back")&&f.current==original);++cases;}
 {Fake f;f.getErrors[3]=-EIO;f.setErrors[2]=-EPERM;ThreadCapacityLease a(f);assert(reason(a.acquire(),"rollback-pending"));assert(reason(a.release(),"restored")&&f.current==original);++cases;}
 {Fake f;ThreadCapacityLease a(f);a.acquire();f.getErrors[4]=-EIO;assert(a.release().active);assert(reason(a.release(),"restored")&&f.current==original);++cases;}
 {Fake f;ThreadCapacityLease a(f);a.acquire();f.setErrors[2]=-EPERM;assert(a.release().active);assert(reason(a.release(),"restored")&&f.current==original);++cases;}
 {Fake f;f.setErrors[2]=-EPERM;{ThreadCapacityLease a(f);a.acquire();}assert(f.current==selected);ThreadCapacityLease b(f);assert(b.acquire().active);assert(reason(b.release(),"restored")&&f.current==original);++cases;}
 {Fake f;f.clip=true;ThreadCapacityLease a(f);assert(a.acquire().selected==mask({9}));assert(reason(a.release(),"restored-constrained")&&f.current==mask({9}));++cases;}
 {Fake f;std::unique_ptr<ThreadCapacityLease> a;std::thread t([&]{a=std::make_unique<ThreadCapacityLease>(f);assert(a->acquire().active);});t.join();auto gets=f.gets,sets=f.sets;assert(reason(a->release(),"owner-exited")&&f.gets==gets&&f.sets==sets);++cases;}
 {Fake f;std::unique_ptr<ThreadCapacityLease> a;std::thread t([&]{a=std::make_unique<ThreadCapacityLease>(f);a->acquire();});t.join();f.current=original;assert(reason(a->acquire(),"selected"));assert(reason(a->release(),"restored")&&f.current==original);++cases;}
 {Fake f;std::unique_ptr<ThreadCapacityLease> a;std::promise<void> acquired,finished;auto end=finished.get_future();pid_t target=0;
  std::thread t([&]{target=f.currentThread();a=std::make_unique<ThreadCapacityLease>(f);a->acquire();acquired.set_value();end.wait();});
  acquired.get_future().wait();assert(reason(a->release(),"restored")&&f.lastTarget==target&&f.current==original);finished.set_value();t.join();++cases;}
 {Fake f,g;ThreadCapacityLease a(f),b(g);a.acquire();assert(b.acquire().status==-EBUSY);a.release();assert(f.current==original&&g.sets==0);++cases;}
 {Fake f;try{ThreadCapacityLease a(f);a.acquire();throw 1;}catch(int){}assert(f.current==original);++cases;}
 // Exercise actual syscalls with the existing allowed mask; fake only capacities.
 class Actual final : public CapacityThreadOps {
  LinuxCapacityThreadOps linux_;unsigned low_;
 public:
  explicit Actual(unsigned low):low_(low){}
  pid_t currentThread() override{return linux_.currentThread();}
  std::optional<CapacityCpuMask> affinity(pid_t tid) override{return linux_.affinity(tid);}
  int setAffinity(pid_t tid,const CapacityCpuMask &m) override{return linux_.setAffinity(tid,m);}
  std::optional<unsigned> capacity(unsigned c) override{return c==low_?200:900;}
 };
 LinuxCapacityThreadOps native;auto before=native.affinity(0);assert(before&&before->any());unsigned low=0;while(!(*before)[low])++low;
 {Actual actual(low);ThreadCapacityLease a(actual);auto r=a.acquire();assert(r.status==0);if(before->count()>1){assert(r.active&&!r.selected[low]);assert(reason(a.release(),"restored"));}assert(native.affinity(0)==before);++cases;}
 std::cout<<"{\"passed\":true,\"cases\":"<<cases<<",\"actual_allowed_mask_restored\":true}\n";
}
