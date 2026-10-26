"""Generate a diagnostic-only FULL ownership patch in a private directory."""
from pathlib import Path
import difflib
import hashlib
import json
import re
import sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/"kernel449"))
import storage
source = storage.mount.mounted_build().parent/"libcamera450-stats-retirement/src/libcamera-v0.7.2"
name = "src/libcamera/pipeline/camss-vfe/camss_vfe.cpp"
original = (source/name).read_text()
assert hashlib.sha256(original.encode()).hexdigest()=="6f91b18a1822f43c459cb72912aea51b257e51644af5d4d5bd13d41e0740a090"
modified = original
anchors = []

def replace(before, after, label):
    global modified
    if modified.count(before) != 1:
        pattern = "\n".join(r"^[ \t]*" + re.escape(line.lstrip(" \t"))
                            for line in before.split("\n"))
        matches = list(re.finditer(pattern, modified, re.MULTILINE))
        assert len(matches) == 1, (label, len(matches))
        before = matches[0].group(0)
    assert modified.count(before) == 1, (label, modified.count(before))
    modified = modified.replace(before, after)
    anchors.append(label)

replace('#include "thread_capacity.h"',
        '#include "thread_capacity.h"\n#include "full_ownership_trace.h"', "include")
replace("  bool toneTraceSaved_ = false;", """  bool toneTraceSaved_ = false;
  camss_diag::Capture fullTrace_;
  void traceFull(camss_diag::EventType type, Request *request = nullptr,
                 FrameBuffer *buffer = nullptr, uint32_t sof = camss_diag::Unknown,
                 uint64_t hardwareNs = 0, int32_t status = 0)
  {
   if (!fullTrace_.active()) return;
   camss_diag::Event e{};
   e.type=uint16_t(type);e.request=reinterpret_cast<uintptr_t>(request);
   e.buffer=reinterpret_cast<uintptr_t>(buffer);e.hardwareNs=hardwareNs;e.sof=sof;
   e.requestSequence=request?request->sequence():camss_diag::Unknown;
   e.lastSof=lastSof_.value_or(camss_diag::Unknown);
   e.activeRequest=reinterpret_cast<uintptr_t>(ipeActive_);
   e.freeFull=freeImages_.size();e.requests=requests_.size();e.waitingFull=images_.size();
   e.coarse=coarseImages_.size();e.histograms=histograms_.size();
   e.statistics=pendingStats_.size();e.associations=internalRequests_.size();e.status=status;
   e.flags=(running_?uint32_t(camss_diag::Running):0u)|
           (ipeActive_?uint32_t(camss_diag::IpeActive):0u)|
           (parameterBusy_?uint32_t(camss_diag::ParameterBusy):0u);
   if(buffer) {
    if(buffer->metadata().status==FrameMetadata::FrameSuccess)e.flags|=camss_diag::BufferSuccess;
    if(buffer->_d()->timestampMonotonic())e.flags|=camss_diag::BufferTimestampMonotonic;
   }
   fullTrace_.record(e);
  }""", "snapshot")
replace("  ++d->epoch_;", """  ++d->epoch_;
  {
   const int status=d->fullTrace_.start(utils::secure_getenv("LIBCAMERA_CAMSS_FULL_TRACE_DIR"),d->epoch_);
   if(status)LOG(CamssVfe,Warning)<<"FULL ownership diagnostic disabled status="<<status;
   d->traceFull(camss_diag::EventType::Start);
  }""", "start-before-stream")
replace("  if (ret) goto error;\n  if(d->coarseEnabled_) {",
        "  if (ret) goto error;\n  d->traceFull(camss_diag::EventType::PoolReady);\n  if(d->coarseEnabled_) {", "pool")
replace("\tauto *d = data(camera);\n\td->running_ = false;",
        "\tauto *d = data(camera);\n d->traceFull(camss_diag::EventType::StopBegin);\n\td->running_ = false;", "stop-begin")
replace("\tif (configured_ == d)\n\t\tconfigured_ = nullptr;\n}\n\nint CamssVfePipeline::queueRequestDevice",
        """\tif (configured_ == d)
\t\tconfigured_ = nullptr;
 d->traceFull(camss_diag::EventType::StopEnd);
 if(d->fullTrace_.active()) {
  const int result=d->fullTrace_.stop();
  LOG(CamssVfe,Info)<<"FULL_OWNERSHIP_TRACE epoch="<<d->epoch_<<" file="<<d->fullTrace_.filename()
   <<" total="<<d->fullTrace_.lastTotal()<<" retained="<<d->fullTrace_.lastRetained()
   <<" overwritten="<<d->fullTrace_.lastOverwritten()<<" result="<<result;
 }
}

int CamssVfePipeline::queueRequestDevice""", "export-after-release")
replace("  auto *d = data(camera);\n  FrameBuffer *buffer = request->findBuffer(&d->stream_);",
        "  auto *d = data(camera);\n  d->traceFull(camss_diag::EventType::RequestEnter,request);\n  FrameBuffer *buffer = request->findBuffer(&d->stream_);", "request-entry")
replace("  if (internal) {if(d->freeImages_.empty())return -ENOBUFS;ife=d->freeImages_.front();}",
        """  if (internal) {
   if(d->freeImages_.empty()){d->traceFull(camss_diag::EventType::NoFreeFull,request);return -ENOBUFS;}
   ife=d->freeImages_.front();
  }""", "no-free")
replace("  if (internal) {d->freeImages_.pop();d->internalRequests_[ife]=request;}\n  int ret = d->image_->queueBuffer(ife);",
        """  if (internal) {
   d->freeImages_.pop();d->internalRequests_[ife]=request;
   d->traceFull(camss_diag::EventType::InternalTake,request,ife);
  }
  d->traceFull(camss_diag::EventType::FullQbufBegin,request,ife);
  int ret = d->image_->queueBuffer(ife);
  d->traceFull(camss_diag::EventType::FullQbufResult,request,ife,camss_diag::Unknown,0,ret);""", "full-qbuf")
replace("   if(internal){d->internalRequests_.erase(ife);d->freeImages_.push(ife);}",
        """   if(internal){
    d->internalRequests_.erase(ife);d->freeImages_.push(ife);
    d->traceFull(camss_diag::EventType::InternalReturn,request,ife,camss_diag::Unknown,0,ret);
   }""", "failed-qbuf-return")
replace("  return 0;\n}\n\n\nRequest *CamssVfeData::imageRequest",
        "  d->traceFull(camss_diag::EventType::RequestAccepted,request,ife);\n  return 0;\n}\n\n\nRequest *CamssVfeData::imageRequest", "accepted")
replace("  if(!running_)return;\n  if(previousPixStart_",
        "  if(!running_)return;\n  traceFull(camss_diag::EventType::PixSof,nullptr,nullptr,sequence,timestamp);\n  if(previousPixStart_", "real-sof")
replace("void CamssVfeData::imageReady(FrameBuffer *buffer)\n{\n",
        """void CamssVfeData::imageReady(FrameBuffer *buffer)
{
 traceFull(camss_diag::EventType::FullDq,imageRequest(buffer),buffer,
           buffer->metadata().status==FrameMetadata::FrameSuccess?buffer->_d()->kernelSequence():camss_diag::Unknown,
           buffer->metadata().timestamp,int32_t(buffer->metadata().status));
""", "full-dq")
replace("void CamssVfeData::coarseReady(FrameBuffer *buffer)\n{\n  if(!running_)return;",
        """void CamssVfeData::coarseReady(FrameBuffer *buffer)
{
  if(!running_)return;
  traceFull(camss_diag::EventType::Pd10Dq,nullptr,buffer,buffer->_d()->kernelSequence(),
            buffer->metadata().timestamp,int32_t(buffer->metadata().status));""", "pd10")
replace("void CamssVfeData::statsReady(FrameBuffer *buffer)\n{\n  if (!running_) return;",
        """void CamssVfeData::statsReady(FrameBuffer *buffer)
{
  if (!running_) return;
  traceFull(camss_diag::EventType::StatsDq,nullptr,buffer,buffer->_d()->kernelSequence(),
            buffer->metadata().timestamp,int32_t(buffer->metadata().status));""", "statistics")
replace("  auto it = pendingStats_.find(id);\n  if (it == pendingStats_.end() || !it->second.submitted || it->second.sof != sof) return;",
        "  traceFull(camss_diag::EventType::StatsDone,nullptr,nullptr,sof,0,statistics.status);\n  auto it = pendingStats_.find(id);\n  if (it == pendingStats_.end() || !it->second.submitted || it->second.sof != sof) return;", "statistics-done")
replace("    if(running_ && ipe_ && processedEnabled_ && sequence!=images_.begin()->first)return;",
        """    if(running_ && ipe_ && processedEnabled_ && sequence!=images_.begin()->first) {
     traceFull(camss_diag::EventType::WaitOlder,request,buffer,sequence);return;
    }""", "wait-older")
replace("    if(running_ && ipe_ && processedEnabled_ && ipeActive_) {",
        "    if(running_ && ipe_ && processedEnabled_ && ipeActive_) {\n     traceFull(camss_diag::EventType::WaitIpe,request,buffer,sequence);", "wait-ipe")
replace("        if(found==coarseImages_.end() && !force) {",
        "        if(found==coarseImages_.end() && !force) {\n         traceFull(camss_diag::EventType::WaitPd10,request,buffer,sequence);", "wait-pd10")
replace("    if(running_ && ipe_ && processedEnabled_)ipeActive_=request;",
        """    if(running_ && ipe_ && processedEnabled_) {
     ipeActive_=request;traceFull(camss_diag::EventType::IpeClaim,request,buffer,sequence);
    }""", "ipe-claim")
replace("   LOG(CamssVfe,Info)<<\"IPE_TONE_QUEUE epoch=\"",
        "   traceFull(camss_diag::EventType::IpeQueue,request,buffer,sequence,buffer->metadata().timestamp,ret);\n   LOG(CamssVfe,Info)<<\"IPE_TONE_QUEUE epoch=\"", "ipe-queue")
replace("  if(it==requests_.end() || it->second.ifeImage!=input || it->second.image!=output)return;",
        """  if(it==requests_.end() || it->second.ifeImage!=input || it->second.image!=output)return;
  traceFull(camss_diag::EventType::ImageProcessed,request,input,input->_d()->kernelSequence(),
            input->metadata().timestamp,success?0:-EIO);""", "ipe-completion")
replace("  if(internalRequests_.erase(ife))freeImages_.push(ife);",
        """  if(internalRequests_.erase(ife)) {
   freeImages_.push(ife);
   traceFull(camss_diag::EventType::InternalReturn,request,ife);
  }
  traceFull(camss_diag::EventType::RequestComplete,request,ife,
            ife->metadata().status==FrameMetadata::FrameSuccess?ife->_d()->kernelSequence():camss_diag::Unknown,
            image->metadata().timestamp,int32_t(image->metadata().status));""", "internal-return-complete")

header_name = "src/libcamera/pipeline/camss-vfe/full_ownership_trace.h"
header = (HERE/"full_ownership_trace.h").read_text()
private = Path("/mnt/e/edk2-samurai-out/kernel452/draft")
private.mkdir(mode=0o700, parents=True, exist_ok=True)
patch = ""
for path, before, after in [(name,original,modified),(header_name,"",header)]:
    destination = private/path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(after)
    patch += "".join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),
                                        fromfile="a/"+path if before else "/dev/null",
                                        tofile="b/"+path))
(HERE/"0063-camss-bounded-full-ownership-trace.patch").write_text(patch)
result = {
    "stage":452,"diagnostic_only":True,"production_source_modified":False,
    "patch_file":"0063-camss-bounded-full-ownership-trace.patch",
    "phone_or_sdk_accessed":False,"base_pipeline_sha256":hashlib.sha256(original.encode()).hexdigest(),
    "draft_pipeline_sha256":hashlib.sha256(modified.encode()).hexdigest(),
    "patch_sha256":hashlib.sha256(patch.encode()).hexdigest(),"hooks":anchors,
    "record_bytes":112,"ring_events":8192,"ring_bytes":917504,
    "default_disabled":True,"preallocate_and_touch_before_stream":True,
    "export_after_queue_and_ipa_stop":True,"hot_path_io":False,"passed":True,
}
enum_block=header.split("enum class EventType : uint16_t {",1)[1].split("};",1)[0]
names=[value.strip() for value in enum_block.split(",")]
assert names.pop()=="Count"
result["event_types"]={str(i):value for i,value in enumerate(names)}
result["flags"]={"1":"running","2":"ipe_active","4":"parameter_busy",
                 "8":"buffer_success","16":"buffer_timestamp_monotonic"}
(HERE/"source-draft-validation.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps(result,indent=2))
