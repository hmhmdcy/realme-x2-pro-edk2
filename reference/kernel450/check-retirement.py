"""Exercise the actual retirement block with synchronous nested callbacks."""
from pathlib import Path
import hashlib,json,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
volume=storage.mount.mounted_build().parent
rel='src/libcamera/pipeline/camss-vfe/camss_vfe.cpp'
tree=storage.candidate()/'src/libcamera-v0.7.2'
original=(volume/'libcamera448-capacity-lease/src/libcamera-v0.7.2'/rel).read_text()
fixed=(tree/rel).read_text()
def block(source,new):
 start=source.index(' while (histogramOrder_.size() > 32) {')
 end=source.index(' if (!running_ || epoch != epoch_) return;',start)
 if new:
  start=source.rindex(' if (!running_ || epoch != epoch_) return;',0,start)
  end=source.index(' if (!running_ || epoch != epoch_) return;',end+1)
 return source[start:end]
old_block=block(original,False);new_block=block(fixed,True)
harness=r'''
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <deque>
#include <functional>
#include <map>
#include <vector>
struct Fixture {
 struct Histogram { uint64_t ipeToken; };
 struct Proxy {
  std::vector<uint64_t> receipts;
  std::function<void()> hook;
  void frameProcessed(uint64_t,uint32_t,uint64_t token,bool success) {
   assert(!success);receipts.push_back(token);
   if(hook){auto callback=std::move(hook);hook={};callback();}
  }
 } proxy;
 Proxy *ipa_=&proxy;
 bool running_=true;
 uint64_t epoch_=1;
 std::deque<uint32_t> histogramOrder_;
 std::map<uint32_t,Histogram> histograms_;
 void add(uint32_t sof,uint64_t token){histogramOrder_.push_back(sof);histograms_.emplace(sof,Histogram{token});}
 Fixture(){for(uint32_t sof=1;sof<=33;++sof)add(sof,sof);}
 void retire(uint64_t epoch) {
  (void)epoch;
@@BLOCK@@
 }
};
int main(){
 {
  Fixture f;f.proxy.hook=[&]{f.add(34,34);f.retire(1);};f.retire(1);
#ifdef BASELINE
  assert((f.proxy.receipts==std::vector<uint64_t>{1,1,2}));
  assert(!f.histograms_.count(3));
#else
  assert((f.proxy.receipts==std::vector<uint64_t>{1,2}));
  assert(f.histograms_.size()==32 && f.histogramOrder_.size()==32 && f.histogramOrder_.front()==3);
#endif
 }
#ifndef BASELINE
 {
  Fixture f;f.retire(1);assert((f.proxy.receipts==std::vector<uint64_t>{1}));
  f.retire(1);assert(f.proxy.receipts.size()==1 && f.histograms_.size()==32);
 }
 {
  Fixture f;f.proxy.hook=[&]{f.running_=false;f.histograms_.clear();f.histogramOrder_.clear();};
  f.retire(1);assert(f.proxy.receipts.size()==1 && f.histogramOrder_.empty());
 }
 {
  Fixture f;f.proxy.hook=[&]{f.epoch_=2;f.histograms_.clear();f.histogramOrder_.clear();for(unsigned i=100;i<133;++i)f.add(i,i);};
  f.retire(1);assert(f.proxy.receipts.size()==1 && f.histogramOrder_.size()==33 && f.histograms_.size()==33);
 }
 {
  Fixture f;f.running_=false;f.retire(1);assert(f.proxy.receipts.empty() && f.histograms_.size()==33);
 }
 {
  Fixture f;f.retire(2);assert(f.proxy.receipts.empty() && f.histograms_.size()==33);
 }
 {
  Fixture f;f.histograms_.at(1).ipeToken=0;f.retire(1);assert(f.proxy.receipts.empty() && f.histograms_.size()==32);
 }
 {
  Fixture f;f.histograms_.erase(1);f.retire(1);assert(f.proxy.receipts.empty() && f.histogramOrder_.size()==32);
 }
#endif
}
'''
for name,body,defines in [('baseline',old_block,['-DBASELINE']),('fixed',new_block,[])]:
 source=P/('retirement-'+name+'.cpp');source.write_text(harness.replace('@@BLOCK@@',body))
 binary=P/('retirement-'+name)
 q=subprocess.run(['g++','-std=c++20','-g','-O1','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer',*defines,str(source),'-o',str(binary)],capture_output=True)
 (P/('retirement-'+name+'-build.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,(q.stdout+q.stderr).decode()
 q=subprocess.run([str(binary)],capture_output=True)
 (P/('retirement-'+name+'-run.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,(q.stdout+q.stderr).decode()
r=dict(stage=450,baseline448_duplicate_and_unacknowledged_entry_loss_reproduced=True,actual_source_block_host_asan_ubsan=True,fixed_cases=8,nested_append_and_reentry_once_only=True,stop_and_epoch_change_preserved=True,missing_or_zero_token_tolerated=True,pipeline_sha256=hashlib.sha256((tree/rel).read_bytes()).hexdigest(),phone_accessed=False,passed=True)
(HERE/'retirement-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
