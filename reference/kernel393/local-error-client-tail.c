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
