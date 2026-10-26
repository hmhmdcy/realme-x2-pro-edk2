"""Connect completed same-SOF PD10 to the existing production request lifecycle."""
from pathlib import Path
import hashlib,json,shutil,sys
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
new=storage.candidate();old=new.parent/'libcamera424-tone-domains'
if new.exists():assert sys.argv[1:]==['--resume-preparation'] and not (HERE/'source-state.json').exists()
else:shutil.copytree(old,new,symlinks=True,ignore=lambda d,n:[x for x in n if x=='pkg' or x.startswith('pkg-before') or x=='__pycache__'])
tree=new/'src/libcamera-v0.7.2';folder=tree/'src/libcamera/pipeline/camss-vfe'
for n in ['camss_ipe.h','camss_ipe.cpp','camss_vfe.cpp']:shutil.copyfile(old/'src/libcamera-v0.7.2/src/libcamera/pipeline/camss-vfe'/n,folder/n)
def replace(t,a,b):
 assert t.count(a)==1,(a,t.count(a));return t.replace(a,b)
h=(folder/'camss_ipe.h').read_text();h=replace(h,'unsigned int count);','unsigned int count, bool pd10 = false);')
h=replace(h,'const qcom_ipe_a5_frame_params *params = nullptr);','const qcom_ipe_a5_frame_params *params = nullptr,\n\t\t  FrameBuffer *coarse = nullptr);')
h=replace(h,'FrameBuffer *original;','FrameBuffer *original;\n\t\tFrameBuffer *coarse;')
h=replace(h,'bool requestsEnabled_ = false;','bool requestsEnabled_ = false, pd10_ = false;')
(folder/'camss_ipe.h').write_text(h)
t=(folder/'camss_ipe.cpp').read_text()
t=replace(t,'namespace libcamera {',"/* Local paired-source ABI, shared with the maintained kernel candidate. */\n#ifndef V4L2_PIX_FMT_QCOM_NV12_PD10\n#define V4L2_PIX_FMT_QCOM_NV12_PD10 v4l2_fourcc('Q','N','1','0')\n#endif\n\nnamespace libcamera {")
t=replace(t,'const V4L2DeviceFormat &format, unsigned int count)','const V4L2DeviceFormat &format, unsigned int count, bool pd10)')
t=replace(t,'opened_ = true;','opened_ = true;\n\tpd10_ = pd10;\n\tif (pd10 && (format.size != Size(640,480) || format.planesCount != 1)) { stop(); return -EINVAL; }')
t=replace(t,'V4L2DeviceFormat negotiated = format;','''V4L2DeviceFormat expected = format;
        if (pd10 && queue == device_.output()) {
            expected.fourcc = V4L2PixelFormat(V4L2_PIX_FMT_QCOM_NV12_PD10);
            expected.planesCount = 2;
            expected.planes[1].bpl = 768; expected.planes[1].size = 46080;
        }
        V4L2DeviceFormat negotiated = expected;''')
a=t.index('\t\tif (!ret && (negotiated.fourcc');z=t.index('\n\t\tif (ret) {',a)
t=t[:a]+'''        if (!ret && (negotiated.fourcc != expected.fourcc || negotiated.size != expected.size || negotiated.planesCount != expected.planesCount)) ret = -EINVAL;
        for (unsigned int i=0; !ret && i<expected.planesCount; ++i)
            if (negotiated.planes[i].bpl != expected.planes[i].bpl || negotiated.planes[i].size != expected.planes[i].size) ret = -EINVAL;
'''+t[z:]
t=replace(t,'<< " requests=" << requestsEnabled_;','<< " requests=" << requestsEnabled_ << " pd10=" << pd10_;')
t=replace(t,'const qcom_ipe_a5_frame_params *params)\n','const qcom_ipe_a5_frame_params *params, FrameBuffer *coarse)\n')
t=replace(t,'if (job.original == input)','if (job.original == input || (coarse && job.coarse == coarse))')
t=replace(t,'if (params && !requestsEnabled_)','''if (bool(coarse) != pd10_ || (coarse && (coarse == input || coarse == output ||
        coarse->planes().size()!=1 || input->planes().size()!=1 ||
        coarse->metadata().status!=FrameMetadata::FrameSuccess ||
        coarse->_d()->kernelSequence()!=input->_d()->kernelSequence()))) return -EINVAL;
    if (params && !requestsEnabled_)''')
a=t.index('\tauto planes = input->planes();');z=t.index('\tjob.request = request;',a)
t=t[:a]+'''    auto planes = input->planes();
    std::vector<FrameBuffer::Plane> joined(planes.begin(),planes.end());
    if (coarse) joined.push_back(coarse->planes()[0]);
    Job job{ input, coarse, std::make_unique<FrameBuffer>(joined) };
    /* Keep both source descriptors and the original SOF until three-way completion.
     * Copy scalar metadata, preserving the wrapper's two-plane metadata storage. */
    auto &metadata=job.input->_d()->metadata();
    metadata.status=input->metadata().status;metadata.sequence=input->metadata().sequence;metadata.timestamp=input->metadata().timestamp;
    for (unsigned int i=0;i<planes.size();++i) metadata.planes()[i]=input->metadata().planes()[i];
    if (coarse) metadata.planes()[planes.size()]=coarse->metadata().planes()[0];
'''+t[z:]
(folder/'camss_ipe.cpp').write_text(t)
t=(folder/'camss_vfe.cpp').read_text()
t=replace(t,'namespace libcamera {',"/* Private coarse transport format, not an application stream. */\n#ifndef V4L2_PIX_FMT_QCOM_PD10_LOCAL\n#define V4L2_PIX_FMT_QCOM_PD10_LOCAL v4l2_fourcc('Q','P','1','0')\n#endif\n\nnamespace libcamera {")
t=replace(t,'MediaEntity *pix;','MediaEntity *pix;\n        MediaEntity *coarse;')
t=replace(t,'void imageReady(FrameBuffer *buffer);','void imageReady(FrameBuffer *buffer);\n void coarseReady(FrameBuffer *buffer);')
t=replace(t,'*ifeImage = nullptr;','*ifeImage = nullptr, *coarse = nullptr;')
t=replace(t,'void finish(uint32_t sequence, bool paired);','void finish(uint32_t sequence, bool paired, bool force = false);')
t=replace(t,'image_, params_, stats_, raw_;','image_, params_, stats_, raw_, coarse_;')
t=replace(t,'std::vector<MediaLink *> path_, rawPath_;','std::vector<MediaLink *> path_, rawPath_;\n MediaLink *coarseLink_ = nullptr;\n bool coarseEnabled_ = false;\n std::vector<std::unique_ptr<FrameBuffer>> coarseBuffers_;\n std::map<uint32_t,FrameBuffer *> coarseImages_;\n std::optional<uint32_t> consumedCoarseSof_;')
t=replace(t,'CamssVfeData::Endpoint endpoint{ nullptr, nullptr, nullptr, entity };','CamssVfeData::Endpoint endpoint{ nullptr, nullptr, nullptr, entity, nullptr };')
t=replace(t,'else if (device.formats().count(V4L2PixelFormat(V4L2_PIX_FMT_NV12)))','else if (device.formats().count(V4L2PixelFormat(V4L2_PIX_FMT_QCOM_PD10_LOCAL)))\n                    endpoint.coarse = other;\n                else if (device.formats().count(V4L2PixelFormat(V4L2_PIX_FMT_NV12)))')
t=replace(t,'image_->bufferReady.connect(this, &CamssVfeData::imageReady);','''image_->bufferReady.connect(this, &CamssVfeData::imageReady);
    if (endpoint.coarse) {
        coarse_=std::make_unique<V4L2VideoDevice>(endpoint.coarse);
        int ret=coarse_->open();if(ret)return ret;
        for(const auto *pad:endpoint.pix->pads()) for(auto *link:pad->links())
            if(link->source()->entity()==endpoint.pix && link->sink()->entity()==endpoint.coarse)coarseLink_=link;
        if(!coarseLink_)return -ENOLINK;
        coarse_->bufferReady.connect(this,&CamssVfeData::coarseReady);
    }''')
t=replace(t,'std::vector<MediaLink *> routes = path_;','coarseEnabled_ = bool(coarse_ && ipe_ && processedEnabled_ && output==Size(640,480));\n std::vector<MediaLink *> routes = path_;\n if(coarseEnabled_) routes.push_back(coarseLink_);')
t=replace(t,'\treturn 0;\n}\n\n\nStreamFormats CamssVfeData::streamFormats', '''    if (coarseEnabled_) {
        V4L2SubdeviceFormat coarse{MEDIA_BUS_FMT_UYYVYY10_0_5X30,Size(160,120),{}};
        ret=pix_->setFormat(coarseLink_->source()->index(),&coarse);
        if(ret || coarse.size!=Size(160,120) || coarse.code!=MEDIA_BUS_FMT_UYYVYY10_0_5X30)return ret?ret:-EINVAL;
        V4L2DeviceFormat wire;wire.fourcc=V4L2PixelFormat(V4L2_PIX_FMT_QCOM_PD10_LOCAL);wire.size=Size(160,120);
        ret=coarse_->setFormat(&wire);
        if(ret || wire.planesCount!=1 || wire.planes[0].bpl!=768 || wire.planes[0].size!=46080 || wire.size!=Size(160,120))return ret?ret:-EINVAL;
    }
    return 0;
}


StreamFormats CamssVfeData::streamFormats''')
t=replace(t,'d->images_.clear(); d->histograms_.clear();','d->coarseImages_.clear();d->consumedCoarseSof_.reset();\n d->images_.clear(); d->histograms_.clear();')
t=replace(t,'if (d->processedEnabled_ && d->ipe_) {\n  V4L2DeviceFormat format;', '''if(d->coarseEnabled_) {
  const unsigned count=d->stream_.configuration().bufferCount+4;
  ret=d->coarse_->allocateBuffers(count,&d->coarseBuffers_);
  if(ret<int(count)){ret=ret<0?ret:-ENOMEM;goto error;}
  for(auto &buffer:d->coarseBuffers_) {ret=d->coarse_->queueBuffer(buffer.get());if(ret)goto error;}
 }
 if (d->processedEnabled_ && d->ipe_) {
  V4L2DeviceFormat format;''')
t=replace(t,'d->ipe_->start(format,d->stream_.configuration().bufferCount)','d->ipe_->start(format,d->stream_.configuration().bufferCount,d->coarseEnabled_)')
t=replace(t,'d->running_ = true;\n for (auto *device','d->running_ = true;\n if(d->coarseEnabled_){ret=d->coarse_->streamOn();if(ret)goto error;}\n for (auto *device')
t=replace(t,'\td->image_->streamOff();','\td->image_->streamOff();\n if(d->coarseEnabled_)d->coarse_->streamOff();')
t=replace(t,'d->internalImages_.clear();d->freeImages_={};d->internalRequests_.clear();','d->coarseImages_.clear();d->consumedCoarseSof_.reset();\n if(d->coarseEnabled_)d->coarse_->releaseBuffers();d->coarseBuffers_.clear();\n d->internalImages_.clear();d->freeImages_={};d->internalRequests_.clear();')
t=replace(t,'void CamssVfeData::finish(uint32_t sequence, bool paired)','void CamssVfeData::finish(uint32_t sequence, bool paired, bool force)')
t=replace(t,'\timages_.erase(it);\n if(!request || !requests_.count(request))return;', '''    if(!request || !requests_.count(request)){images_.erase(it);return;}
    if(coarseEnabled_ && running_ && buffer->metadata().status==FrameMetadata::FrameSuccess) {
        auto found=coarseImages_.find(sequence);
        if(found==coarseImages_.end() && !force) {
            if(!deadline_.isRunning())deadline_.start(std::chrono::milliseconds(250));
            return;
        }
        consumedCoarseSof_=sequence;
        if(found==coarseImages_.end())buffer->_d()->metadata().status=FrameMetadata::FrameError;
        else {requests_.at(request).coarse=found->second;coarseImages_.erase(found);}
    }
    images_.erase(it);''')
t=replace(t,'ipe_->queue(buffer,output,tone.empty()?nullptr:&packet)','ipe_->queue(buffer,output,tone.empty()?nullptr:&packet,requests_.at(request).coarse)')
t=replace(t,'<<" revision="<<toneRevision<<" fresh="<<toneFresh<<" bytes="<<tone.size()<<" result="<<ret;', '<<" revision="<<toneRevision<<" fresh="<<toneFresh<<" bytes="<<tone.size()<<" pd10="<<coarseEnabled_<<" result="<<ret;')
t=replace(t,' it->second.imageFinished=true;\n it->second.failed |= !success;', ''' if(it->second.coarse) {
  FrameBuffer *coarse=it->second.coarse;it->second.coarse=nullptr;
  if(running_ && coarse_->queueBuffer(coarse))success=false;
 }
 it->second.imageFinished=true;
 it->second.failed |= !success;''')
t=replace(t,'while (!images_.empty()) finish(images_.begin()->first,false);','while (!images_.empty()) finish(images_.begin()->first,histograms_.count(images_.begin()->first),true);')
at=t.index('void CamssVfeData::statsReady(FrameBuffer *buffer)')
t=t[:at]+'''void CamssVfeData::coarseReady(FrameBuffer *buffer)
{
 if(!running_)return;
 const uint32_t sof=buffer->_d()->kernelSequence();
 if(buffer->metadata().status!=FrameMetadata::FrameSuccess ||
    (consumedCoarseSof_ && sof<=*consumedCoarseSof_) || coarseImages_.count(sof)) {
  if(coarse_->queueBuffer(buffer))LOG(CamssVfe,Error)<<"PD10 requeue failed";
  return;
 }
 coarseImages_[sof]=buffer;
 LOG(CamssVfe,Info)<<"PD10_READY epoch="<<epoch_<<" sof="<<sof<<" bytes="<<buffer->metadata().planes()[0].bytesused;
 if(images_.count(sof) && histograms_.count(sof))finish(sof,true);
 else completeMissingStatistics();
 /* Retain up to one application queue's worth of unclaimed SOFs. In-flight
  * IPE sources have already left this map and remain owned by PendingFrame. */
 while(coarseImages_.size()>stream_.configuration().bufferCount) {
  auto it=coarseImages_.begin();FrameBuffer *old=it->second;coarseImages_.erase(it);
  if(coarse_->queueBuffer(old))LOG(CamssVfe,Error)<<"PD10 stale requeue failed";
 }
}

'''+t[at:]
(folder/'camss_vfe.cpp').write_text(t)
names=['src/libcamera/pipeline/camss-vfe/'+n for n in ['camss_vfe.cpp','camss_ipe.cpp','camss_ipe.h']]
r=dict(stage=431,baseline_stage=424,source=str(tree),source_prepared=True,source_hashes=[dict(path=n,sha256=hashlib.sha256((tree/n).read_bytes()).hexdigest()) for n in names],private_ipa_version=3,ipa_mathematics_unchanged=True,installed=False,passed=True)
(HERE/'source-state.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
