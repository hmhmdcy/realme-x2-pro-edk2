/* Test the actual coarseReady() body while FULL images await the IPE. */
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <map>
#include <optional>
#include <set>
#include <vector>
#include <cstdio>
struct Sink { template<class T> Sink &operator<<(const T &) { return *this; } } sink;
#define LOG(...) sink
struct FrameMetadata { enum {FrameSuccess=0};int status=FrameSuccess;struct Plane{unsigned bytesused=46080;};std::vector<Plane> p{{}};const auto &planes()const{return p;} };
struct FrameBuffer { uint32_t sof;FrameMetadata m;FrameBuffer *_d(){return this;}uint32_t kernelSequence(){return sof;}const FrameMetadata &metadata()const{return m;} };
struct Device { std::vector<FrameBuffer*> returned;int queueBuffer(FrameBuffer *b){assert(std::find(returned.begin(),returned.end(),b)==returned.end());returned.push_back(b);return 0;} };
struct Stream { struct Configuration{unsigned bufferCount=4;}cfg;const auto &configuration()const{return cfg;} };
class CamssVfeData {
public:
 bool running_=true,busy=true;uint64_t epoch_=1;std::optional<uint32_t> consumedCoarseSof_;
 std::map<uint32_t,FrameBuffer*> coarseImages_,images_;std::set<uint32_t> histograms_;Stream stream_;Device dev,*coarse_=&dev;
 void coarseReady(FrameBuffer *buffer);
 void completeMissingStatistics(){}
 void finish(uint32_t sof,bool){if(busy)return;assert(!images_.empty()&&images_.begin()->first==sof);assert(coarseImages_.count(sof));coarseImages_.erase(sof);images_.erase(sof);consumedCoarseSof_=sof;}
};
#include "coarse-ready-body-private.cpp"
int main()
{
 CamssVfeData d;std::vector<FrameBuffer> frames(21);for(unsigned i=0;i<frames.size();++i){frames[i].sof=i;d.histograms_.insert(i);}
 for(unsigned i:{2u,3u,4u})d.images_[i]=&frames[i];
 for(auto &frame:frames){d.coarseReady(&frame);assert(d.coarseImages_.size()<=4);}
 assert(d.coarseImages_.size()==4&&d.coarseImages_.count(2)&&d.coarseImages_.count(3)&&d.coarseImages_.count(4)&&d.coarseImages_.count(20));
 for(unsigned i:{2u,3u,4u})assert(std::find(d.dev.returned.begin(),d.dev.returned.end(),&frames[i])==d.dev.returned.end());
 d.busy=false;d.finish(2,true);assert(!d.images_.count(2)&&d.coarseImages_.count(3));
 FrameBuffer late;late.sof=1;d.coarseReady(&late);assert(d.dev.returned.back()==&late);
 puts("COARSE_RETENTION_PASS actual_body=1 waiting_full_pd10_pinned=3 unclaimed_bounded=1 stale_requeued=1");
}
