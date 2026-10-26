/* SPDX-License-Identifier: GPL-2.0-only */
/* Reuse the actual V4L2 allocation/pattern helpers, not their old test main. */
#define main baseline386_main
#include "../kernel386/m2m-client.c"
#undef main

struct test_context {
 int fd;
 struct stream s;
 struct memory in, out;
};
static const unsigned output_type=V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE;
static const unsigned capture_type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;
static const char *status_path="/sys/bus/platform/devices/ac10000.icp/m2m_status";
static void snapshot(char *text, size_t bytes)
{
 FILE *f=fopen(status_path,"r");assert(f && fgets(text,bytes,f));fclose(f);
 text[strcspn(text,"\n")]=0;
}
static uint64_t metric(const char *text,const char *key)
{
 char pattern[80];snprintf(pattern,sizeof(pattern),"\"%s\":",key);
 const char *p=strstr(text,pattern);assert(p);return strtoull(p+strlen(pattern),NULL,10);
}
static struct test_context setup(const char *node,unsigned id)
{
 struct test_context c={.fd=open(node,O_RDWR|O_NONBLOCK|O_CLOEXEC),
  .s={.id=id,.width=640,.height=480,.stride=640,.frames=2}};
 assert(c.fd>=0);format(c.fd,&c.s,0);
 request(c.fd,output_type,V4L2_MEMORY_MMAP,2);
 request(c.fd,capture_type,V4L2_MEMORY_MMAP,2);
 c.in=allocate(c.fd,output_type,0,0);c.out=allocate(c.fd,capture_type,0,0);
 return c;
}
static void enqueue(struct test_context *c)
{
 memset(c->out.address,0xa7,c->out.length);
 queue(c->fd,&c->s,output_type,0,&c->in,0);
 queue(c->fd,&c->s,capture_type,0,&c->out,0);
}
static void stream_on(struct test_context *c)
{
 unsigned a=output_type,b=capture_type;
 call(c->fd,VIDIOC_STREAMON,&a);call(c->fd,VIDIOC_STREAMON,&b);
}
static void stream_off(struct test_context *c,int capture_first)
{
 unsigned a=capture_first?capture_type:output_type;
 unsigned b=capture_first?output_type:capture_type;
 call(c->fd,VIDIOC_STREAMOFF,&a);call(c->fd,VIDIOC_STREAMOFF,&b);
}
static void unmap_context(struct test_context *c)
{
 assert(!munmap(c->in.address,c->in.length));assert(!munmap(c->out.address,c->out.length));
 c->in.address=c->out.address=MAP_FAILED;
}
static void close_context(struct test_context *c)
{
 if(c->in.address!=MAP_FAILED)unmap_context(c);
 assert(!close(c->fd));c->fd=-1;
}
static void verify_frame(struct test_context *c)
{
 struct v4l2_plane p={};struct v4l2_buffer b=dequeue(c->fd,capture_type,&c->s,&p);
 assert(b.index==0 && b.sequence==0 && b.timestamp.tv_sec==1000+c->s.id);
 unsigned bad=0;unsigned char *data=c->out.address;
 for(unsigned y=0;y<c->s.height;y++)for(unsigned x=0;x<c->s.width;x++)
  bad+=data[y*c->s.stride+x]!=luma(c->s.id,0,x,y);
 assert(!bad);struct v4l2_plane in={};dequeue(c->fd,output_type,&c->s,&in);
}
static int log_tail(void)
{
 int fd=open("/dev/kmsg",O_RDONLY|O_NONBLOCK|O_CLOEXEC);assert(fd>=0);
 assert(lseek(fd,0,SEEK_END)>=0);return fd;
}
static void wait_configured(int fd)
{
 struct timespec begin,now;assert(!clock_gettime(CLOCK_MONOTONIC,&begin));
 char line[8192];
 for(;;){
  ssize_t n=read(fd,line,sizeof(line)-1);
  if(n>0){line[n]=0;if(strstr(line,"ac10000.icp: A5 IPE CONFIG_IO acknowledged"))return;continue;}
  if(n<0 && errno==EINTR)continue;
  assert(n<0 && errno==EAGAIN);struct pollfd p={.fd=fd,.events=POLLIN};
  int ret=poll(&p,1,100);assert(ret>=0);
  assert(!clock_gettime(CLOCK_MONOTONIC,&now) && now.tv_sec-begin.tv_sec<8);
 }
}
static void cancel_case(const char *node,unsigned id,int close_active,int peer)
{
 char before[2048],after[2048];snapshot(before,sizeof(before));
 struct test_context c=setup(node,id),other={.fd=-1};
 if(peer){other=setup(node,20+id);enqueue(&other);}
 enqueue(&c);int log=log_tail();stream_on(&c);wait_configured(log);assert(!close(log));
 if(peer)stream_on(&other);
 if(close_active)close_context(&c);else stream_off(&c,id==1);
 if(peer){verify_frame(&other);stream_off(&other,0);close_context(&other);}
 if(!close_active){enqueue(&c);stream_on(&c);verify_frame(&c);stream_off(&c,0);close_context(&c);}
 snapshot(after,sizeof(after));
 assert(metric(after,"cancelled")>metric(before,"cancelled"));
 assert(metric(after,"failed")==metric(before,"failed"));
 assert(!metric(after,"users") && !metric(after,"orphans"));
 printf("{\"case\":%u,\"close_active\":%s,\"peer\":%s,\"configured_marker_observed_before_abort\":true,\"before\":%s,\"after\":%s,\"passed\":true}\n",id,close_active?"true":"false",peer?"true":"false",before,after);fflush(stdout);
}
static void expect_error(struct test_context *c,unsigned type)
{
 struct timespec begin,now;assert(!clock_gettime(CLOCK_MONOTONIC,&begin));
 for(;;){
  struct v4l2_plane p={};struct v4l2_buffer b={.type=type,.memory=c->s.dmabuf?V4L2_MEMORY_DMABUF:V4L2_MEMORY_MMAP,.length=1,.m.planes=&p};
  int ret=ioctl(c->fd,VIDIOC_DQBUF,&b);
  if(!ret){assert(b.flags&V4L2_BUF_FLAG_ERROR);return;}
  if(errno==EIO)return;
  assert(errno==EAGAIN || errno==EINTR);
  assert(!clock_gettime(CLOCK_MONOTONIC,&now) && now.tv_sec-begin.tv_sec<8);
  struct pollfd f={.fd=c->fd,.events=POLLIN|POLLOUT};assert(poll(&f,1,100)>=0);
 }
}
static void rejected_alias(const char *node)
{
 char before[2048],after[2048];snapshot(before,sizeof(before));
 struct test_context exporter=setup(node,30),peer=setup(node,31);
 struct test_context bad={.fd=open(node,O_RDWR|O_NONBLOCK|O_CLOEXEC),.s={.id=32,.width=640,.height=480,.stride=640,.dmabuf=1}};
 assert(bad.fd>=0);format(bad.fd,&bad.s,0);
 struct v4l2_exportbuffer e={.type=output_type,.index=0,.flags=O_RDWR|O_CLOEXEC};call(exporter.fd,VIDIOC_EXPBUF,&e);
 request(bad.fd,output_type,V4L2_MEMORY_DMABUF,2);request(bad.fd,capture_type,V4L2_MEMORY_DMABUF,2);
 unsigned bytes=640*480*3/2;
 struct v4l2_plane p={.length=exporter.in.length,.bytesused=bytes,.m.fd=e.fd};
 struct v4l2_buffer b={.type=output_type,.memory=V4L2_MEMORY_DMABUF,.length=1,.m.planes=&p};
 pattern(&exporter.s,exporter.in.address,0);call(bad.fd,VIDIOC_QBUF,&b);
 b.type=capture_type;p.bytesused=0;call(bad.fd,VIDIOC_QBUF,&b);
 enqueue(&peer);int log=log_tail();stream_on(&bad);wait_configured(log);assert(!close(log));
 stream_on(&peer);
 expect_error(&bad,capture_type);expect_error(&bad,output_type);
 expect_error(&peer,capture_type);expect_error(&peer,output_type);
 stream_off(&bad,0);stream_off(&peer,0);
 assert(!close(bad.fd));assert(!close(e.fd));close_context(&exporter);close_context(&peer);
 snapshot(after,sizeof(after));
 assert(metric(after,"failed")==metric(before,"failed")+2);
 assert(metric(after,"completed")==metric(before,"completed"));
 assert(strstr(after,"\"fatal\":false") && !metric(after,"users"));
 struct test_context recovered=setup(node,33);enqueue(&recovered);stream_on(&recovered);verify_frame(&recovered);stream_off(&recovered,0);close_context(&recovered);
 char recovery[2048];snapshot(recovery,sizeof(recovery));
 assert(metric(recovery,"completed")==metric(after,"completed")+1);
 printf("{\"case\":4,\"same_dmabuf_alias_rejected\":true,\"peer_queue_error_verified\":true,\"reopen_recovery_pixel_verified\":true,\"hardware_fault_injection\":false,\"before\":%s,\"after\":%s,\"recovery\":%s,\"passed\":true}\n",before,after,recovery);fflush(stdout);
}
int inherited392_main(int argc,char **argv)
{
 assert(argc==2 || (argc==3 && !strcmp(argv[2],"--remaining")));
 if(argc==2){
  cancel_case(argv[1],0,0,0);
  cancel_case(argv[1],1,0,0);
  cancel_case(argv[1],2,1,0);
 }
 cancel_case(argv[1],3,0,1);
 rejected_alias(argv[1]);
 return 0;
}

/* Extend392 with a peer that keeps running while the bad queue is repaired. */
static void enqueue_sequence(struct test_context *c,unsigned sequence)
{
 memset(c->out.address,0xa7,c->out.length);
 if(c->s.dmabuf){
  /* These exports have exact sizeimage capacity; use offset0. The older
   * 386 padded-offset fixture intentionally allocated extra sensor rows.
   */
  pattern(&c->s,c->in.address,sequence);
  struct v4l2_plane p={.length=c->in.length,.bytesused=c->s.stride*c->s.height*3/2,.m.fd=c->in.dma};
  struct v4l2_buffer b={.type=output_type,.memory=V4L2_MEMORY_DMABUF,.length=1,.m.planes=&p,.field=V4L2_FIELD_NONE};
  b.timestamp.tv_sec=1000+c->s.id;b.timestamp.tv_usec=sequence*1000;call(c->fd,VIDIOC_QBUF,&b);
  p.length=c->out.length;p.bytesused=0;p.m.fd=c->out.dma;b.type=capture_type;call(c->fd,VIDIOC_QBUF,&b);
 }else{
  queue(c->fd,&c->s,output_type,0,&c->in,sequence);
  queue(c->fd,&c->s,capture_type,0,&c->out,sequence);
 }
}
static void verify_sequence(struct test_context *c,unsigned sequence)
{
 struct v4l2_plane p={};struct v4l2_buffer b=dequeue(c->fd,capture_type,&c->s,&p);
 assert(b.index==0 && b.sequence==sequence && b.timestamp.tv_sec==1000+c->s.id && b.timestamp.tv_usec==sequence*1000);
 unsigned bad=0;unsigned char *data=c->out.address;
 for(unsigned y=0;y<c->s.height;y++)for(unsigned x=0;x<c->s.width;x++)bad+=data[y*c->s.stride+x]!=luma(c->s.id,sequence,x,y);
 assert(!bad);struct v4l2_plane in={};dequeue(c->fd,output_type,&c->s,&in);
}
static void isolated_alias(const char *node)
{
 char before[2048],during[2048],repaired[2048],after[2048];snapshot(before,sizeof(before));
 struct test_context exporter=setup(node,40),peer=setup(node,41);
 struct test_context bad={.fd=open(node,O_RDWR|O_NONBLOCK|O_CLOEXEC),.s={.id=42,.width=640,.height=480,.stride=640,.dmabuf=1}};
 assert(bad.fd>=0);format(bad.fd,&bad.s,0);
 struct v4l2_exportbuffer e={.type=output_type,.index=0,.flags=O_RDWR|O_CLOEXEC},f={.type=capture_type,.index=0,.flags=O_RDWR|O_CLOEXEC};
 call(exporter.fd,VIDIOC_EXPBUF,&e);call(exporter.fd,VIDIOC_EXPBUF,&f);
 request(bad.fd,output_type,V4L2_MEMORY_DMABUF,2);request(bad.fd,capture_type,V4L2_MEMORY_DMABUF,2);
 struct v4l2_plane p={.length=exporter.in.length,.bytesused=640*480*3/2,.m.fd=e.fd};
 struct v4l2_buffer b={.type=output_type,.memory=V4L2_MEMORY_DMABUF,.length=1,.m.planes=&p};
 pattern(&exporter.s,exporter.in.address,0);call(bad.fd,VIDIOC_QBUF,&b);
 b.type=capture_type;p.bytesused=0;call(bad.fd,VIDIOC_QBUF,&b);
 enqueue(&peer);int log=log_tail();stream_on(&bad);wait_configured(log);assert(!close(log));stream_on(&peer);
 expect_error(&bad,capture_type);expect_error(&bad,output_type);
 verify_sequence(&peer,0);snapshot(during,sizeof(during));
 assert(metric(during,"failed")==metric(before,"failed")+1 && metric(during,"completed")==metric(before,"completed")+1);
 assert(metric(during,"stops")==metric(before,"stops") && strstr(during,"\"fatal\":false") && strstr(during,"\"running\":true"));
 /* The malformed context remains open; another request must still succeed. */
 enqueue_sequence(&peer,1);verify_sequence(&peer,1);
 /* Repair only the bad queue, while the peer's hardware session stays live. */
 stream_off(&bad,0);bad.in=exporter.in;bad.out=exporter.out;bad.in.dma=e.fd;bad.out.dma=f.fd;
 enqueue_sequence(&bad,0);stream_on(&bad);verify_sequence(&bad,0);snapshot(repaired,sizeof(repaired));
 assert(metric(repaired,"failed")==metric(before,"failed")+1 && metric(repaired,"completed")==metric(before,"completed")+3);
 assert(metric(repaired,"starts")==metric(before,"starts")+1 && metric(repaired,"stops")==metric(before,"stops"));
 assert(strstr(repaired,"\"fatal\":false") && strstr(repaired,"\"running\":true"));
 stream_off(&bad,0);stream_off(&peer,0);assert(!close(bad.fd));assert(!close(e.fd) && !close(f.fd));close_context(&exporter);close_context(&peer);
 snapshot(after,sizeof(after));assert(!metric(after,"users") && !metric(after,"orphans") && metric(after,"stops")==metric(before,"stops")+1);
 printf("{\"case\":\"local-input-error\",\"same_dma_alias_rejected\":true,\"peer_two_distinct_frames_verified\":true,\"bad_context_kept_open_during_peer_reuse\":true,\"same_fd_repaired_while_peer_session_live\":true,\"no_backend_restart_until_last_session_stopped\":true,\"before\":%s,\"during\":%s,\"repaired\":%s,\"after\":%s,\"passed\":true}\n",before,during,repaired,after);fflush(stdout);
}
int main(int argc,char **argv)
{
 assert(argc==2);isolated_alias(argv[1]);cancel_case(argv[1],3,0,1);return 0;
}
