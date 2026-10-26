/* The production doQueueRequests() method is included verbatim. */
#include <cassert>
#include <functional>
#include <queue>
#include <set>
#include <vector>
#include <iostream>
struct Request {
 struct Private { bool prepared_=true; } data;
 int id;
 Private *_d() {return &data;}
};
struct Camera {
 struct Private {std::queue<Request *> waitingRequests_;std::vector<Request *> queuedRequests_;} data;
 Private *_d() {return &data;}
};
struct PipelineHandler {
 unsigned maxQueuedRequestsDevice_=4;
 std::function<void(Request *)> submit;
 void doQueueRequest(Request *r) {submit(r);}
 void doQueueRequests(Camera *camera);
};
#include "ordering-method.inc"
int main()
{
 PipelineHandler pipe;Camera a,b;Request first{{},1},second{{},2},third{{},3},other{{},9};
 std::vector<int> hardware;
 a.data.waitingRequests_.push(&first);a.data.waitingRequests_.push(&second);
 b.data.waitingRequests_.push(&other);
 pipe.submit=[&](Request *r) {
  if(r==&first){a.data.waitingRequests_.push(&third);pipe.doQueueRequests(&a);pipe.doQueueRequests(&b);}
  hardware.push_back(r->id);
 };
 pipe.doQueueRequests(&a);
 assert((hardware==std::vector<int>{9,1,2,3}));
 assert(a.data.waitingRequests_.empty() && b.data.waitingRequests_.empty());
 hardware.clear();second.data.prepared_=false;a.data.waitingRequests_.push(&second);
 pipe.doQueueRequests(&a);assert(hardware.empty());
 second.data.prepared_=true;pipe.doQueueRequests(&a);assert((hardware==std::vector<int>{2}));
 hardware.clear();a.data.waitingRequests_.push(&third);a.data.queuedRequests_.resize(4);
 pipe.doQueueRequests(&a);assert(hardware.empty());a.data.queuedRequests_.clear();
 pipe.doQueueRequests(&a);assert((hardware==std::vector<int>{3}));
 std::cout<<"PASS nested same camera ordered; other camera progresses; prepare/limit wakeups"<<std::endl;
}
