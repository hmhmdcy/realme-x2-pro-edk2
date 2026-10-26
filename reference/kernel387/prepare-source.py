"""Connect the real CAMSS pipeline to the separately acquired IPE endpoint."""
from pathlib import Path
import difflib,hashlib,json,shutil
import storage,host
HERE=Path(__file__).resolve().parent
old=storage.previous.candidate();new=storage.candidate();assert not new.exists()
shutil.copytree(old,new,symlinks=True,ignore=lambda d,n:[x for x in n if x=='pkg' or x.startswith('pkg-before') or x=='__pycache__'])
base=new/'src/libcamera-v0.7.2';name='src/libcamera/pipeline/camss-vfe/camss_vfe.cpp'
p=base/name;before=p.read_text();s=before
assert hashlib.sha256(p.read_bytes()).hexdigest()=='3806f439548bb99f60046477d24e527cd3d8f51cfb7b8402ff484fdae45cc5fd'
def replace(a,b):
 global s
 assert s.count(a)==1,(a,s.count(a))
 s=s.replace(a,b)
replace('#include "hardware_focus.h"','#include "hardware_focus.h"\n#include "camss_ipe.h"')
replace(' void rawReady(FrameBuffer *buffer);',' void rawReady(FrameBuffer *buffer);\n void imageProcessed(FrameBuffer *input, FrameBuffer *output, bool success);')
replace('  FrameBuffer *image = nullptr, *raw = nullptr;','  FrameBuffer *image = nullptr, *raw = nullptr, *ifeImage = nullptr;')
replace(' bool rawEnabled_ = false, processedEnabled_ = true;',' bool rawEnabled_ = false, processedEnabled_ = true;\n std::unique_ptr<CamssIpe> ipe_;')
replace('\tCamssVfeData *configured_ = nullptr;','\tCamssVfeData *configured_ = nullptr;\n\tstd::shared_ptr<MediaDevice> ipeMedia_;')
replace(''' if (d->processedEnabled_) ret=d->image_->importBuffers(d->stream_.configuration().bufferCount);
 else {
  ret=d->image_->allocateBuffers(4,&d->internalImages_);
  if (ret >= 4) {for(auto &buffer:d->internalImages_) d->freeImages_.push(buffer.get());ret=0;}
  else ret=ret<0?ret:-ENOMEM;
 }
 if (ret) goto error;''',''' if (d->processedEnabled_ && !d->ipe_) ret=d->image_->importBuffers(d->stream_.configuration().bufferCount);
 else {
  const unsigned int count=d->processedEnabled_?d->stream_.configuration().bufferCount:4;
  ret=d->image_->allocateBuffers(count,&d->internalImages_);
  if (ret >= int(count)) {for(auto &buffer:d->internalImages_) d->freeImages_.push(buffer.get());ret=0;}
  else ret=ret<0?ret:-ENOMEM;
 }
 if (ret) goto error;
 if (d->processedEnabled_ && d->ipe_) {
  V4L2DeviceFormat format;
  ret=d->image_->getFormat(&format);
  if (!ret) ret=d->ipe_->start(format,d->stream_.configuration().bufferCount);
  if (ret) goto error;
 }''')
replace('\td->image_->streamOff();','\td->image_->streamOff();\n\tif (d->ipe_) d->ipe_->stop();')
replace(' if (!buffer) {if(d->freeImages_.empty())return -ENOBUFS;buffer=d->freeImages_.front();}', ''' const bool internal = !d->processedEnabled_ || bool(d->ipe_);
 FrameBuffer *ife = buffer;
 if (internal) {if(d->freeImages_.empty())return -ENOBUFS;ife=d->freeImages_.front();}
 if (!buffer) buffer=ife;''')
replace(''' d->requests_.emplace(request,CamssVfeData::PendingFrame{buffer,raw,false,!raw,false});
 if (!d->processedEnabled_) {d->freeImages_.pop();d->internalRequests_[buffer]=request;}
 int ret = d->image_->queueBuffer(buffer);''',''' d->requests_.emplace(request,CamssVfeData::PendingFrame{buffer,raw,ife,false,!raw,false});
 if (internal) {d->freeImages_.pop();d->internalRequests_[ife]=request;}
 int ret = d->image_->queueBuffer(ife);''')
replace('  if(!d->processedEnabled_){d->internalRequests_.erase(buffer);d->freeImages_.push(buffer);}', '  if(internal){d->internalRequests_.erase(ife);d->freeImages_.push(ife);}')
replace('const uint32_t imageSof=frame.image->_d()->kernelSequence()', 'const uint32_t imageSof=frame.ifeImage->_d()->kernelSequence()')
replace(''' FrameBuffer *image=frame.image,*raw=frame.raw;
 if(frame.failed){image->_d()->metadata().status=FrameMetadata::FrameError;if(raw)raw->_d()->metadata().status=FrameMetadata::FrameError;}
 requests_.erase(it);
 if(processedEnabled_)handler()->completeBuffer(request,image);
 else {internalRequests_.erase(image);freeImages_.push(image);}''',''' FrameBuffer *image=frame.image,*raw=frame.raw,*ife=frame.ifeImage;
 if(frame.failed){image->_d()->metadata().status=FrameMetadata::FrameError;if(raw)raw->_d()->metadata().status=FrameMetadata::FrameError;}
 requests_.erase(it);
 /* Release the internal association before any application completion. */
 if(internalRequests_.erase(ife))freeImages_.push(ife);
 if(processedEnabled_)handler()->completeBuffer(request,image);''')
# Cancellation of IFE before IPE adoption also restores app metadata.
a='''  auto &frame=requests_.at(request);frame.imageFinished=true;frame.failed=true;
  tryComplete(request);'''
assert s.count(a)==2
s=s.replace(a,'''  imageProcessed(buffer,requests_.at(request).image,false);''')
replace(''' requests_.at(request).imageFinished=true;
 if(buffer->metadata().status!=FrameMetadata::FrameSuccess)requests_.at(request).failed=true;
 tryComplete(request);
 if(images_.empty() && requests_.empty())deadline_.stop();
}

void CamssVfeData::expired()''',''' FrameBuffer *output=requests_.at(request).image;
 if (ipe_ && processedEnabled_ && running_ && buffer->metadata().status==FrameMetadata::FrameSuccess) {
  int ret=ipe_->queue(buffer,output);
  if (ret) imageProcessed(buffer,output,false);
 } else imageProcessed(buffer,output,buffer->metadata().status==FrameMetadata::FrameSuccess);
 if(images_.empty() && requests_.empty())deadline_.stop();
}

void CamssVfeData::imageProcessed(FrameBuffer *input,FrameBuffer *output,bool success)
{
 Request *request=imageRequest(input);
 auto it=requests_.find(request);
 if(it==requests_.end() || it->second.ifeImage!=input || it->second.image!=output)return;
 if(input!=output) {
  output->_d()->metadata()=input->metadata();
  output->_d()->setKernelSequence(input->_d()->kernelSequence());
  output->_d()->setTimestampMonotonic(input->_d()->timestampMonotonic());
 }
 it->second.imageFinished=true;
 it->second.failed |= !success;
 tryComplete(request);
}

void CamssVfeData::expired()''')
replace('''\t/* Group by the PIX subdevice's adjacent nodes and metadata FourCCs. */''','''\tDeviceMatch ipeMatch("SM8150 IPE");
\tipeMatch.add("qcom-ipe-a5-source");
\tipeMedia_ = acquireMediaDevice(enumerator, ipeMatch);
\t/* Group by the PIX subdevice's adjacent nodes and metadata FourCCs. */''')
replace('''\t\t\tstd::set<Stream *> streams{ &d->stream_ };''','''\t\t\tif (ipeMedia_) {
\t\t\t\tMediaEntity *source=ipeMedia_->getEntityByName("qcom-ipe-a5-source");
\t\t\t\td->ipe_=std::make_unique<CamssIpe>(source->deviceNode());
\t\t\t\td->ipe_->processed.connect(d.get(),&CamssVfeData::imageProcessed);
\t\t\t}
\t\t\tstd::set<Stream *> streams{ &d->stream_ };''')
p.write_text(s)
patch=''.join(difflib.unified_diff(before.splitlines(keepends=True),s.splitlines(keepends=True),fromfile='a/'+name,tofile='b/'+name))
for leaf in ['camss_ipe.h','camss_ipe.cpp']:
 content=(HERE/leaf).read_text();target=p.parent/leaf;target.write_text(content)
 patch+=''.join(difflib.unified_diff([],content.splitlines(keepends=True),fromfile='/dev/null',tofile='b/'+str(Path(name).parent/leaf)))
meson=p.parent/'meson.build';beforeMeson=meson.read_text();afterMeson=beforeMeson.replace("files('camss_vfe.cpp')","files('camss_vfe.cpp', 'camss_ipe.cpp')");assert beforeMeson!=afterMeson
meson.write_text(afterMeson)
patch+=''.join(difflib.unified_diff(beforeMeson.splitlines(keepends=True),afterMeson.splitlines(keepends=True),fromfile='a/'+str(Path(name).parent/'meson.build'),tofile='b/'+str(Path(name).parent/'meson.build')))
(HERE/'camss-ipe-pipeline.patch').write_text(patch);(HERE/'camss-vfe-after.cpp').write_text(s)
report=dict(stage=387,candidate=str(new),pipeline_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),installed=False,common_dispatcher_unchanged=True,ipa_unchanged=True,kernel_unchanged=True)
(HERE/'source-state.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
