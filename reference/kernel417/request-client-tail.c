/* SPDX-License-Identifier: GPL-2.0-only */
#include <linux/media.h>
#include <linux/qcom-ipe-a5.h>
#include "request-fixture.h"

static const unsigned modes[FRAMES] = { 0, 1, 2, 2, 3, 4, 0, 1 };

static void params_for(struct qcom_ipe_a5_frame_params *p, unsigned mode)
{
	memset(p,0,sizeof(*p));
	if (!mode) return;
	p->version=1;p->size=sizeof(*p);p->colour=fixed_chain;
	p->colour.modules|=QCOM_IPE_A5_COLOUR_CC;
	p->colour.cc.matrix[0]=p->colour.cc.matrix[4]=p->colour.cc.matrix[8]=128;
	if (mode==2) { p->flags=QCOM_IPE_A5_GAMMA;return; }
	if (mode<3) return;
	p->flags=QCOM_IPE_A5_LTM;
	p->ltm.iq.rgb2y[0]=19;p->ltm.iq.rgb2y[1]=38;p->ltm.iq.rgb2y[2]=7;
	p->ltm.iq.y_ratio_max=1023;p->ltm.iq.image_processing=1;
	p->ltm.iq.local_adaptation=1;
	for(unsigned b=0;b<2;b++)for(unsigned i=0;i<64;i++)
		p->ltm.la[b][i].base=mode==3?2048:1024;
	for(unsigned i=0;i<12;i++)p->ltm.weight[i]=0x0101;
}

static int controls(int fd,int req,struct qcom_ipe_a5_frame_params *p,int get)
{
	struct v4l2_ext_control c={.id=V4L2_CID_QCOM_IPE_A5_FRAME_PARAMS,.size=sizeof(*p),.ptr=p};
	struct v4l2_ext_controls cs={.which=req<0?V4L2_CTRL_WHICH_CUR_VAL:V4L2_CTRL_WHICH_REQUEST_VAL,
		.request_fd=req,.count=1,.controls=&c};
	return ioctl(fd,get?VIDIOC_G_EXT_CTRLS:VIDIOC_S_EXT_CTRLS,&cs);
}

static void request_buffer(int fd,struct stream *s,unsigned type,unsigned i,
			   struct memory *m,unsigned seq,int req)
{
	unsigned offset=s->dmabuf && type==V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE?16:0;
	struct v4l2_plane p={.length=m->length,.data_offset=offset};
	struct v4l2_buffer b={.type=type,.index=i,.length=1,.m.planes=&p,
		.memory=s->dmabuf?V4L2_MEMORY_DMABUF:V4L2_MEMORY_MMAP};
	if(s->dmabuf)p.m.fd=m->dma;
	if(type==V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE){
		pattern(s,m->address+offset,seq);p.bytesused=offset+s->stride*s->height*3/2;
		b.timestamp.tv_sec=1000+s->id;b.timestamp.tv_usec=seq*1000;
		s->result[seq].input_crc=crc32(m->address+offset,s->stride*s->height*3/2);
	}
	if(req>=0){b.flags=V4L2_BUF_FLAG_REQUEST_FD;b.request_fd=req;}
	call(fd,VIDIOC_QBUF,&b);
}

static void set_request(int fd,int req,unsigned mode)
{
	struct qcom_ipe_a5_frame_params p;params_for(&p,mode);
	assert(!controls(fd,req,&p,0));
	/* S_EXT_CTRLS must have copied the user payload at this point. */
	memset(&p,0xa5,sizeof(p));
}

static void check_controls(int fd,int req,unsigned mode)
{
	struct pollfd pfd={.fd=req,.events=POLLPRI};
	assert(poll(&pfd,1,2000)==1 && (pfd.revents&POLLPRI));
	struct qcom_ipe_a5_frame_params p,want;params_for(&want,mode);memset(&p,0x5a,sizeof(p));
	assert(!controls(fd,req,&p,1) && !memcmp(&p,&want,sizeof(p)));
}

static void dump_request(const struct stream *s,unsigned seq,const void *p,unsigned bytes)
{
	char path[512];snprintf(path,sizeof(path),"%s/request-%u-%u-private.nv12",s->directory,s->id,seq);
	int fd=open(path,O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC,0600);assert(fd>=0);
	const unsigned char *q=p;while(bytes){ssize_t n=write(fd,q,bytes);assert(n>0);q+=n;bytes-=n;}
	assert(!fsync(fd) && !close(fd));
}

static void run_requests(struct stream *s,int media)
{
	const unsigned src=V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE,dst=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;
	int fd=open(s->node,O_RDWR|O_NONBLOCK|O_CLOEXEC),exporter=-1;assert(fd>=0);
	unsigned bytes=format(fd,s,0).fmt.pix_mp.plane_fmt[0].sizeimage;
	struct v4l2_query_ext_ctrl query={.id=V4L2_CID_QCOM_IPE_A5_FRAME_PARAMS};call(fd,VIDIOC_QUERY_EXT_CTRL,&query);
	assert(query.type==V4L2_CTRL_TYPE_U8 && query.elems==6008 && query.elem_size==1);
	struct qcom_ipe_a5_frame_params p={};errno=0;
	assert(controls(fd,-1,&p,0)==-1 && errno==EACCES);
	p.version=1;p.size=sizeof(p);p.gamma.base[0][0]=1024;errno=0;
	assert(controls(fd,-1,&p,0)==-1 && errno==ERANGE);
	struct memory input[BUFFERS],output[BUFFERS];int requests[BUFFERS];
	if(s->dmabuf){
		exporter=open(s->node,O_RDWR|O_NONBLOCK|O_CLOEXEC);assert(exporter>=0);format(exporter,s,2);
		request(exporter,src,V4L2_MEMORY_MMAP,2*BUFFERS);
		for(unsigned i=0;i<BUFFERS;i++){input[i]=allocate(exporter,src,i,1);output[i]=allocate(exporter,src,BUFFERS+i,1);}
		request(fd,src,V4L2_MEMORY_DMABUF,BUFFERS);request(fd,dst,V4L2_MEMORY_DMABUF,BUFFERS);
	}else{
		request(fd,src,V4L2_MEMORY_MMAP,BUFFERS);request(fd,dst,V4L2_MEMORY_MMAP,BUFFERS);
		for(unsigned i=0;i<BUFFERS;i++){input[i]=allocate(fd,src,i,0);output[i]=allocate(fd,dst,i,0);}
	}
	for(unsigned i=0;i<BUFFERS;i++)call(media,MEDIA_IOC_REQUEST_ALLOC,&requests[i]);
	struct v4l2_plane bad_plane={.length=input[0].length,.bytesused=bytes};
	struct v4l2_buffer bad_field={.type=src,.index=0,.length=1,.m.planes=&bad_plane,
		.memory=s->dmabuf?V4L2_MEMORY_DMABUF:V4L2_MEMORY_MMAP,
		.field=V4L2_FIELD_INTERLACED,.flags=V4L2_BUF_FLAG_REQUEST_FD,.request_fd=requests[0]};
	if(s->dmabuf)bad_plane.m.fd=input[0].dma;
	errno=0;assert(ioctl(fd,VIDIOC_QBUF,&bad_field)==-1 && errno==EINVAL);
	/* Empty request and buffer-only request must be rejected before DMA. */
	errno=0;assert(ioctl(requests[0],MEDIA_REQUEST_IOC_QUEUE,NULL)==-1 && errno==ENOENT);
	request_buffer(fd,s,src,0,&input[0],0,requests[0]);errno=0;
	assert(ioctl(requests[0],MEDIA_REQUEST_IOC_QUEUE,NULL)==-1 && errno==ENOENT);
	call(requests[0],MEDIA_REQUEST_IOC_REINIT,NULL);
	for(unsigned i=0;i<BUFFERS;i++){
		set_request(fd,requests[i],modes[i]);
		memset(output[i].address,0xa7,output[i].length);
		request_buffer(fd,s,src,i,&input[i],i,requests[i]);
		request_buffer(fd,s,dst,i,&output[i],i,-1);
		call(requests[i],MEDIA_REQUEST_IOC_QUEUE,NULL);
	}
	call(fd,VIDIOC_STREAMON,(void *)&src);call(fd,VIDIOC_STREAMON,(void *)&dst);
	for(unsigned seq=0;seq<FRAMES;seq++){
		struct v4l2_plane op={},ip={};struct v4l2_buffer b=dequeue(fd,dst,s,&op),in=dequeue(fd,src,s,&ip);
		assert(b.index<BUFFERS && in.index<BUFFERS && b.sequence==seq && in.sequence==seq);
		assert(b.timestamp.tv_sec==1000+s->id && b.timestamp.tv_usec==seq*1000 && op.bytesused==bytes);
		unsigned char *out=output[b.index].address;unsigned offset=s->dmabuf?16:0;
		dump_request(s,seq,out,bytes);
		assert(s->result[seq].input_crc==crc32(input[in.index].address+offset,bytes));
		for(unsigned i=bytes;i<output[b.index].length;i++)assert(out[i]==0xa7);
		unsigned different=0;uint64_t ysum=0;for(unsigned y=0;y<s->height;y++)for(unsigned x=0;x<s->width;x++){
			unsigned v=out[y*s->stride+x];ysum+=v;different+=v!=luma(s->id,seq,x,y);
			if(modes[seq]==0)assert(v==luma(s->id,seq,x,y));
			if(modes[seq]==2)assert(v==0);
			if(modes[seq]>=3 && y>=16 && y<64 && x<640 && x%80>=16 && x%80<64)
				assert(v==(modes[seq]==3?128:64));
		}
		if(modes[seq]==2)for(unsigned y=0;y<s->height/2;y++)for(unsigned x=0;x<s->width;x++)assert(out[s->stride*s->height+y*s->stride+x]==128);
		check_controls(fd,requests[in.index],modes[seq]);
		printf("{\"case\":%u,\"sequence\":%u,\"mode\":%u,\"format\":%d,\"width\":%u,\"stride\":%u,\"dmabuf\":%d,\"crc\":%u,\"y_different\":%u,\"y_sum\":%llu,\"passed\":true}\n",s->id,seq,modes[seq],s->nv21,s->width,s->stride,s->dmabuf,crc32(out,bytes),different,(unsigned long long)ysum);fflush(stdout);
		if(seq+BUFFERS<FRAMES){
			call(requests[in.index],MEDIA_REQUEST_IOC_REINIT,NULL);set_request(fd,requests[in.index],modes[seq+BUFFERS]);
			memset(out,0xa7,output[b.index].length);
			request_buffer(fd,s,src,in.index,&input[in.index],seq+BUFFERS,requests[in.index]);
			request_buffer(fd,s,dst,b.index,&output[b.index],seq+BUFFERS,-1);
			call(requests[in.index],MEDIA_REQUEST_IOC_QUEUE,NULL);
		}
	}
	if(!s->close_streaming){call(fd,VIDIOC_STREAMOFF,(void *)&src);call(fd,VIDIOC_STREAMOFF,(void *)&dst);}
	close(fd);
	for(unsigned i=0;i<BUFFERS;i++){close(requests[i]);munmap(input[i].address,input[i].length);munmap(output[i].address,output[i].length);if(s->dmabuf){close(input[i].dma);close(output[i].dma);}}
	if(exporter>=0)close(exporter);
}

int main(int argc,char **argv)
{
	assert(argc==4);int media=open(argv[2],O_RDWR|O_CLOEXEC);assert(media>=0);
	struct stream cases[]={
		{.id=0,.width=640,.height=480,.stride=640},
		{.id=1,.width=650,.height=480,.stride=672,.nv21=1,.dmabuf=1,.close_streaming=1},
	};
	for(unsigned i=0;i<2;i++){cases[i].node=argv[1];cases[i].directory=argv[3];run_requests(&cases[i],media);}
	close(media);puts("{\"frames\":16,\"request_reuse\":true,\"queued_user_memory_overwritten\":true,\"passed\":true}");return 0;
}
