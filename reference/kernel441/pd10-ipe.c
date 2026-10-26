/* SPDX-License-Identifier: GPL-2.0-only */
/* Bounded real PD10 replay through the ordinary media-request queues. */
#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/media.h>
#include <linux/qcom-ipe-a5.h>
#include <poll.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <time.h>
#include <unistd.h>

struct memory { unsigned char *p; unsigned bytes; };
static const unsigned out_type=V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE;
static const unsigned cap_type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;
static unsigned width,height,full_bytes,coarse_width,coarse_height,coarse_stride,coarse_bytes,scratch_bytes;

static int call(int fd,unsigned long command,void *arg)
{
	int ret;
	do { ret=ioctl(fd,command,arg); } while(ret<0 && errno==EINTR);
	if(ret<0) { fprintf(stderr,"IOCTL command=%lx errno=%d\n",command,errno);exit(2); }
	return ret;
}
static void read_exact(const char *directory,const char *name,void *out,unsigned bytes)
{
	char path[1024];snprintf(path,sizeof(path),"%s/%s",directory,name);
	int fd=open(path,O_RDONLY|O_CLOEXEC);assert(fd>=0);unsigned char *p=out;
	for(unsigned n=0;n<bytes;) { ssize_t count=read(fd,p+n,bytes-n);assert(count>0);n+=count; }
	unsigned char end;assert(!read(fd,&end,1));assert(!close(fd));
}
static void save(const char *directory,unsigned mode,const char *name,const void *data,unsigned bytes)
{
	char path[1024];snprintf(path,sizeof(path),"%s/mode-%u-%s.bin",directory,mode,name);
	int fd=open(path,O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC,0600);assert(fd>=0);const unsigned char *p=data;
	for(unsigned n=0;n<bytes;) { ssize_t count=write(fd,p+n,bytes-n);assert(count>0);n+=count; }
	assert(!fsync(fd) && !close(fd));
}
static uint64_t hash(const unsigned char *p,unsigned bytes)
{
	uint64_t value=1469598103934665603ULL;
	for(unsigned i=0;i<bytes;i++)value=(value^p[i])*1099511628211ULL;
	return value;
}
static void format(int fd,unsigned type)
{
	struct v4l2_format f={.type=type};
	f.fmt.pix_mp.width=width;f.fmt.pix_mp.height=height;
	f.fmt.pix_mp.pixelformat=type==out_type?V4L2_PIX_FMT_QCOM_NV12_PD10:V4L2_PIX_FMT_NV12;
	f.fmt.pix_mp.plane_fmt[0].bytesperline=width;
	call(fd,VIDIOC_S_FMT,&f);
	assert(f.fmt.pix_mp.width==width && f.fmt.pix_mp.height==height && f.fmt.pix_mp.num_planes==(type==out_type?2:1));
	assert(f.fmt.pix_mp.plane_fmt[0].sizeimage==full_bytes);
	if(type==out_type)assert(f.fmt.pix_mp.plane_fmt[1].sizeimage==coarse_bytes && f.fmt.pix_mp.plane_fmt[1].bytesperline==coarse_stride);
}
static void allocate(int fd,unsigned type,struct memory *memory)
{
	struct v4l2_requestbuffers request={.count=1,.type=type,.memory=V4L2_MEMORY_MMAP};
	call(fd,VIDIOC_REQBUFS,&request);assert(request.count==1);
	struct v4l2_plane planes[2]={};
	struct v4l2_buffer b={.type=type,.memory=V4L2_MEMORY_MMAP,.length=type==out_type?2:1,.m.planes=planes};
	call(fd,VIDIOC_QUERYBUF,&b);
	for(unsigned i=0;i<b.length;i++) {
		memory[i].bytes=planes[i].length;
		memory[i].p=mmap(NULL,planes[i].length,PROT_READ|PROT_WRITE,MAP_SHARED,fd,planes[i].m.mem_offset);
		assert(memory[i].p!=MAP_FAILED);
		memset(memory[i].p,0xa7,memory[i].bytes);
	}
}
static void enqueue(int fd,unsigned type,int request,const struct memory *memory,unsigned mode)
{
	struct v4l2_plane planes[2]={};unsigned count=type==out_type?2:1;
	for(unsigned i=0;i<count;i++) {
		planes[i].length=memory[i].bytes;
		if(type==out_type)planes[i].bytesused=i?coarse_bytes:full_bytes;
	}
	struct v4l2_buffer b={.type=type,.memory=V4L2_MEMORY_MMAP,.length=count,.m.planes=planes};
	if(type==out_type) { b.flags=V4L2_BUF_FLAG_REQUEST_FD;b.request_fd=request;b.timestamp.tv_sec=100+mode; }
	call(fd,VIDIOC_QBUF,&b);
}
static void dequeue(int fd,unsigned type,unsigned mode)
{
	struct v4l2_plane planes[2]={};
	struct v4l2_buffer b={.type=type,.memory=V4L2_MEMORY_MMAP,.length=type==out_type?2:1,.m.planes=planes};
	struct timespec start,now;assert(!clock_gettime(CLOCK_MONOTONIC,&start));
	for(;;) {
		assert(!clock_gettime(CLOCK_MONOTONIC,&now));
		assert(now.tv_sec-start.tv_sec<15);
		int ret=ioctl(fd,VIDIOC_DQBUF,&b);
		if(!ret)break;
		assert(errno==EAGAIN || errno==EINTR);
		struct pollfd p={.fd=fd,.events=POLLIN|POLLOUT};
		int ready=poll(&p,1,1000);assert(ready>=0 || errno==EINTR);
	}
	fprintf(stderr,"DQ type=%u flags=%x bytes=%u sequence=%u timestamp=%ld\n",type,b.flags,planes[0].bytesused,b.sequence,(long)b.timestamp.tv_sec);
	assert(!(b.flags&V4L2_BUF_FLAG_ERROR) && b.index==0 && b.sequence==0 && b.timestamp.tv_sec==100+(long)mode);
	assert(planes[0].bytesused==full_bytes);
	if(type==out_type)assert(planes[1].bytesused==coarse_bytes);
}
static unsigned scratch(unsigned char *data,unsigned capacity)
{
	int fd=open("/sys/bus/platform/devices/ac10000.icp/ltm_scratch",O_RDONLY|O_CLOEXEC);assert(fd>=0);unsigned used=0;
	while(used<capacity) { ssize_t n=read(fd,data+used,capacity-used);assert(n>=0);if(!n)break;used+=n; }
	assert(!close(fd) && used==scratch_bytes+16);return used;
}
int main(int argc,char **argv)
{
	assert(argc==7);
 width=strtoul(argv[4],NULL,10);height=strtoul(argv[5],NULL,10);scratch_bytes=strtoul(argv[6],NULL,10);
 assert(width>=128 && width<=1920 && height>=128 && height<=1080 && !((width|height)&1) && scratch_bytes<=0x40000);
 full_bytes=width*height*3/2;coarse_width=((width+7)/4)&~1U;coarse_height=((height+7)/4)&~1U;
 coarse_stride=((coarse_width*4+191)/192)*192;coarse_bytes=coarse_stride*((coarse_height+7)/8)*4;assert(sizeof(struct qcom_ipe_a5_frame_params)==6008);
	const char *directory=argv[3];
	struct qcom_ipe_a5_frame_params params;
	read_exact(directory,"parameters-private.bin",&params,sizeof(params));
	assert(params.version==1 && params.size==sizeof(params) && (params.flags&QCOM_IPE_A5_LTM));
	assert(params.ltm.iq.data_collection && params.ltm.iq.image_processing && params.ltm.iq.mask_filter);
	unsigned char *data=malloc(0x40000+16);assert(data);
	for(unsigned mode=0;mode<4;mode++) {
		int fd=open(argv[1],O_RDWR|O_NONBLOCK|O_CLOEXEC);assert(fd>=0);
		int media=open(argv[2],O_RDWR|O_CLOEXEC);assert(media>=0);
		format(fd,out_type);format(fd,cap_type);
		struct memory input[2],output[1];allocate(fd,out_type,input);allocate(fd,cap_type,output);
		read_exact(directory,"full-private.bin",input[0].p,full_bytes);
		read_exact(directory,"pd10-private.bin",input[1].p,coarse_bytes);
		if(mode==1 || mode==2)for(unsigned row=0;row<coarse_height/2;row++)for(unsigned group=0;group<coarse_width/2;group++) {
			unsigned char *p=input[1].p+row*coarse_stride+group*8;
			memset(p,mode==1?0:255,4);p[4]=p[5]=128;p[6]=mode==1?0:255;p[7]=0;
		}
		uint64_t full_hash=hash(input[0].p,full_bytes),coarse_hash=hash(input[1].p,coarse_bytes);
		int request=-1;call(media,MEDIA_IOC_REQUEST_ALLOC,&request);assert(request>=0);
		struct v4l2_ext_control control={.id=V4L2_CID_QCOM_IPE_A5_FRAME_PARAMS,.size=sizeof(params),.ptr=&params};
		struct v4l2_ext_controls controls={.which=V4L2_CTRL_WHICH_REQUEST_VAL,.count=1,.request_fd=request,.controls=&control};
		call(fd,VIDIOC_S_EXT_CTRLS,&controls);
		enqueue(fd,cap_type,-1,output,mode);enqueue(fd,out_type,request,input,mode);
		unsigned type=cap_type;call(fd,VIDIOC_STREAMON,&type);type=out_type;call(fd,VIDIOC_STREAMON,&type);
		call(request,MEDIA_REQUEST_IOC_QUEUE,NULL);
		dequeue(fd,cap_type,mode);dequeue(fd,out_type,mode);
		assert(hash(input[0].p,full_bytes)==full_hash && hash(input[1].p,coarse_bytes)==coarse_hash);
		for(unsigned i=full_bytes;i<output[0].bytes;i++)assert(output[0].p[i]==0xa7);
		unsigned bytes=scratch(data,0x40000+16);save(directory,mode,"scratch-private",data,bytes);
		save(directory,mode,"output-private",output[0].p,full_bytes);
		uint32_t header[4];memcpy(header,data,16);assert(header[0]==1 && header[1]==scratch_bytes);
		printf("{\"mode\":%u,\"full_hash\":\"%016llx\",\"pd10_hash\":\"%016llx\",\"output_hash\":\"%016llx\",\"scratch_crc\":%u,\"scratch_changed_bytes\":%u,\"passed\":true}\n",
			mode,(unsigned long long)full_hash,(unsigned long long)coarse_hash,(unsigned long long)hash(output[0].p,full_bytes),header[2],header[3]);fflush(stdout);
		type=out_type;call(fd,VIDIOC_STREAMOFF,&type);type=cap_type;call(fd,VIDIOC_STREAMOFF,&type);
		for(unsigned i=0;i<2;i++)assert(!munmap(input[i].p,input[i].bytes));
		assert(!munmap(output[0].p,output[0].bytes));assert(!close(request) && !close(media) && !close(fd));
	}
	free(data);puts("PD10_IPE_RESULT result=0 frames=4");return 0;
}
