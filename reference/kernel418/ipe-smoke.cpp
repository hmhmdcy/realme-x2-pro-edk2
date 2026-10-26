/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* Exercise the actual candidate CamssIpe and libcamera event dispatcher. */
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <fcntl.h>
#include <iostream>
#include <map>
#include <memory>
#include <string>
#include <unistd.h>
#include <libcamera/base/event_dispatcher.h>
#include <libcamera/base/thread.h>
#include <libcamera/base/timer.h>
#include "libcamera/internal/framebuffer.h"
#include "libcamera/internal/mapped_framebuffer.h"
#include "libcamera/internal/media_device.h"
#include "libcamera/internal/v4l2_videodevice.h"
#include "camss_ipe.h"
#include "request-params.h"

using namespace libcamera;
static constexpr std::array<unsigned,8> modes={0,1,2,2,3,4,0,1};
static uint32_t crc(const uint8_t *p,size_t n)
{
	uint32_t c=0;for(size_t i=0;i<n;i++){c^=p[i];for(unsigned bit=0;bit<8;bit++)c=(c>>1)^((c&1)?0xedb88320:0);}return c;
}
static uint8_t yvalue(unsigned x,unsigned y)
{
	unsigned row=y/80;return !row?16+32*(x/80):row<4?128:row==4?64:192;
}
static void pattern(uint8_t *p,unsigned width,unsigned stride,bool nv21)
{
	memset(p,0x55,stride*480*3/2);
	for(unsigned y=0;y<480;y++)for(unsigned x=0;x<width;x++)p[y*stride+x]=yvalue(x,y);
	p+=stride*480;
	for(unsigned y=0;y<240;y++)for(unsigned x=0;x<width;x++){
		unsigned row=2*y/80,col=x/80;
		unsigned u=!row?128:row<4?96+32*(col%3):64+48*(col%4);
		unsigned v=!row?128:row<4?96+32*(row-1):208-48*(col/2);
		p[y*stride+x]=((x&1)^nv21)?v:u;
	}
}
static void dump(const std::string &path,const uint8_t *data,size_t bytes)
{
	int fd=open(path.c_str(),O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC,0600);assert(fd>=0);
	while(bytes){ssize_t n=write(fd,data,bytes);assert(n>0);data+=n;bytes-=n;}assert(!fsync(fd));close(fd);
}

class Capture : public Object
{
public:
	CamssIpe *ipe=nullptr;
	std::array<FrameBuffer *,2> input{},output{};
	std::array<std::unique_ptr<MappedFrameBuffer>,2> inMap{},outMap{};
	std::map<FrameBuffer *,unsigned> sequences;
	std::array<uint32_t,8> inputCrc{};
	unsigned id=0,width=640,stride=640,completed=0,cancelled=0;
	bool nv21=false,cancelling=false,timedout=false;
	std::string root;
	void queue(unsigned i,unsigned sequence)
	{
		unsigned bytes=stride*480*3/2;
		auto &meta=input[i]->_d()->metadata();meta.status=FrameMetadata::FrameSuccess;
		meta.sequence=100+sequence;meta.timestamp=1000000000000ULL+sequence*1000000ULL;
		meta.planes()[0].bytesused=bytes;
		pattern(inMap[i]->planes()[0].data(),width,stride,nv21);
		memset(outMap[i]->planes()[0].data(),0xa7,outMap[i]->planes()[0].size());
		inputCrc[sequence]=crc(inMap[i]->planes()[0].data(),bytes);
		sequences[output[i]]=sequence;
		qcom_ipe_a5_frame_params p{};params_for(&p,modes[sequence]);
		assert(!ipe->queue(input[i],output[i],&p));
		memset(&p,0xa5,sizeof(p));
	}
	void done(FrameBuffer *in,FrameBuffer *out,bool success)
	{
		unsigned i=out==output[0]?0:1;assert(out==output[i] && in==input[i]);
		unsigned sequence=sequences.at(out),mode=modes[sequence];sequences.erase(out);
		assert(in->metadata().sequence==100+sequence && in->metadata().timestamp==1000000000000ULL+sequence*1000000ULL);
		if(cancelling){assert(!success);cancelled++;return;}
		assert(success);
		unsigned bytes=stride*480*3/2;const auto *p=outMap[i]->planes()[0].data();
		dump(root+"/wrapper-"+std::to_string(id)+"-"+std::to_string(sequence)+"-private.nv12",p,bytes);
		assert(inputCrc[sequence]==crc(inMap[i]->planes()[0].data(),bytes));
		assert(out->metadata().timestamp==in->metadata().timestamp && out->metadata().planes()[0].bytesused==bytes);
		for(unsigned n=bytes;n<outMap[i]->planes()[0].size();n++)assert(p[n]==0xa7);
		for(unsigned y=0;y<480;y++)for(unsigned x=0;x<width;x++){
			unsigned v=p[y*stride+x];
			if(!mode)assert(v==yvalue(x,y));
			if(mode==2)assert(v==0);
			if(mode>=3 && y>=16 && y<64 && x<640 && x%80>=16 && x%80<64)assert(v==(mode==3?128:64));
		}
		if(mode==2)for(unsigned y=0;y<240;y++)for(unsigned x=0;x<width;x++)assert(p[stride*480+y*stride+x]==128);
		completed++;
		std::cout<<"{\"case\":"<<id<<",\"sequence\":"<<sequence<<",\"mode\":"<<mode<<",\"crc\":"<<crc(p,bytes)<<",\"passed\":true}"<<std::endl;
		if(sequence+2<modes.size())queue(i,sequence+2);
		else if(completed==modes.size() && id==1)ipe->stop(); /* callback reentry */
	}
	void deadline(){timedout=true;ipe->stop();}
};

int main(int argc,char **argv)
{
	assert(argc==4);auto media=std::make_shared<MediaDevice>(argv[2]);
	assert(!media->populate() && media->driver()=="qcom-ipe-a5" && media->acquire());
	for(unsigned id=0;id<2;id++){
		Capture c;c.id=id;c.root=argv[3];c.width=id?650:640;c.stride=id?672:640;c.nv21=id;
		V4L2DeviceFormat format;format.fourcc=V4L2PixelFormat(id?V4L2_PIX_FMT_NV21:V4L2_PIX_FMT_NV12);
		format.size=Size(c.width,482);format.planesCount=1;format.planes[0].bpl=c.stride;
		V4L2M2MDevice exporter(argv[1]);assert(!exporter.open());assert(!exporter.output()->setFormat(&format));
		std::vector<std::unique_ptr<FrameBuffer>> exported,buffers;assert(exporter.output()->allocateBuffers(4,&exported)>=4);
		/* The exporter describes logical Y/UV planes at height482. The
		 * exerciser uses one contiguous DMABUF plane with extra tail space,
		 * so describe that storage explicitly instead of creating a hole.
		 */
		for(const auto &buffer:exported){
			auto planes=buffer->planes();unsigned length=0;
			for(const auto &plane:planes){assert(plane.fd==planes[0].fd && plane.offset==length);length+=plane.length;}
			std::vector<FrameBuffer::Plane> flat={{planes[0].fd,0,length}};
			buffers.push_back(std::make_unique<FrameBuffer>(flat));
		}
		format.size.height=480;format.planes[0].size=c.stride*480*3/2;
		CamssIpe ipe(argv[1],media);c.ipe=&ipe;
		for(unsigned i=0;i<2;i++){
			c.input[i]=buffers[i].get();c.output[i]=buffers[i+2].get();
			c.inMap[i]=std::make_unique<MappedFrameBuffer>(c.input[i],MappedFrameBuffer::MapFlag::ReadWrite);
			c.outMap[i]=std::make_unique<MappedFrameBuffer>(c.output[i],MappedFrameBuffer::MapFlag::ReadWrite);
			assert(c.inMap[i]->isValid() && c.outMap[i]->isValid());
		}
		ipe.processed.connect(&c,&Capture::done);assert(!ipe.start(format,2));
		Timer deadline;deadline.timeout.connect(&c,&Capture::deadline);deadline.start(std::chrono::seconds(20));
		c.queue(0,0);c.queue(1,1);
		while(c.completed<modes.size() && !c.timedout)Thread::current()->eventDispatcher()->processEvents();
		deadline.stop();assert(!c.timedout && c.completed==8 && c.sequences.empty());ipe.stop();
		/* STREAMOFF must return adopted jobs once, without committing success. */
		assert(!ipe.start(format,2));c.cancelling=true;c.queue(0,0);c.queue(1,1);ipe.stop();
		assert(c.cancelled==2 && c.sequences.empty());exporter.close();
		std::cout<<"{\"case\":"<<id<<",\"frames\":8,\"cancelled\":2,\"restart\":true,\"passed\":true}"<<std::endl;
	}
	media->release();std::cout<<"{\"actual_libcamera_wrapper\":true,\"frames\":16,\"cancelled\":4,\"passed\":true}"<<std::endl;
	return 0;
}
