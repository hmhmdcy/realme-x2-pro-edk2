/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include <array>
#include <cassert>
#include <chrono>
#include <cstdlib>
#include <iostream>
#include <libcamera/base/event_dispatcher.h>
#include <libcamera/base/event_notifier.h>
#include <libcamera/base/thread.h>
#include <libcamera/base/timer.h>
#include <libcamera/base/unique_fd.h>
#include <memory>
#include <sys/eventfd.h>
#include <unistd.h>
using namespace libcamera;
struct Test {
 std::array<UniqueFD,3> fds;
 std::array<std::unique_ptr<EventNotifier>,3> notifiers;
 std::array<unsigned int,3> counts{};
 EventDispatcher *dispatcher=Thread::current()->eventDispatcher();
 Timer timer;unsigned int levels=1;bool timerCase=false,rearm=false;
 void receive(unsigned int i) {
  uint64_t value=0;assert(read(fds[i].get(),&value,sizeof(value))==sizeof(value)&&value==1);++counts[i];
  if(!timerCase||i+1!=levels)notifiers[i]->setEnabled(false);
  if(!rearm&&i+1<levels)dispatcher->processEvents();
 }
 void a(){receive(0);}void b(){receive(1);}void c(){receive(2);}
 void expire(){notifiers[levels-1]->setEnabled(false);}
 void run(unsigned int depth,bool timed) {
  levels=depth;timerCase=timed;
  for(unsigned int i=0;i<levels;++i) {
   fds[i]=UniqueFD(eventfd(0,EFD_NONBLOCK|EFD_CLOEXEC));assert(fds[i].isValid());
   notifiers[i]=std::make_unique<EventNotifier>(fds[i].get(),EventNotifier::Read);
  }
  notifiers[0]->activated.connect(this,&Test::a);
  if(levels>1)notifiers[1]->activated.connect(this,&Test::b);
  if(levels>2)notifiers[2]->activated.connect(this,&Test::c);
  if(timerCase){timer.timeout.connect(this,&Test::expire);timer.start(std::chrono::milliseconds(0));}
  uint64_t one=1;for(unsigned int i=0;i<levels;++i)assert(write(fds[i].get(),&one,sizeof(one))==sizeof(one));
  dispatcher->processEvents();
  for(unsigned int i=0;i<levels;++i)assert(counts[i]==1&&!notifiers[i]->enabled());
  rearm=true;timerCase=false;notifiers[levels-1]->setEnabled(true);assert(write(fds[levels-1].get(),&one,sizeof(one))==sizeof(one));
  dispatcher->processEvents();assert(counts[levels-1]==2);
 }
};
int main(int argc,char **argv)
{
 assert(argc==3);Test test;test.run(std::atoi(argv[1]),std::atoi(argv[2]));
 std::cout<<"DISPATCHER_REGRESSION_PASS depth="<<argv[1]<<" timer="<<argv[2]<<std::endl;
}
