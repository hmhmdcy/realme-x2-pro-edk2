static void set_gamma_mode(unsigned mode)
{
 const char *path="/sys/module/camss_icp_a5_m2m/parameters/test_gamma_mode";
 int fd=open(path,O_WRONLY|O_CLOEXEC);assert(fd>=0);char text[32];int n=snprintf(text,sizeof(text),"%u\n",mode);assert(write(fd,text,n)==n);assert(!close(fd));
 FILE *f=fopen(path,"r");unsigned actual;assert(f && fscanf(f,"%u",&actual)==1 && actual==mode);fclose(f);
}
static void dump_chain_file(const char *root,unsigned format,unsigned mode,const char *kind,const void *data,unsigned bytes)
{
 char path[512];snprintf(path,sizeof(path),"%s/format-%u-mode-%u-%s-private.nv12",root,format,mode,kind);
 int fd=open(path,O_CREAT|O_EXCL|O_WRONLY|O_CLOEXEC,0600);assert(fd>=0);const unsigned char *p=data;
 while(bytes){ssize_t n=write(fd,p,bytes);assert(n>0);p+=n;bytes-=n;}assert(!fsync(fd) && !close(fd));
 int directory=open(root,O_RDONLY|O_DIRECTORY|O_CLOEXEC);assert(directory>=0 && !fsync(directory) && !close(directory));
}
int main(int argc,char **argv)
{
 assert(argc==3);char before[2048],after[2048];snapshot(before,sizeof(before));unsigned bytes=640*480*3/2;
 unsigned char *pair=malloc(bytes);assert(pair);
 for(unsigned format=0;format<2;format++)for(unsigned mode=0;mode<10;mode++){
  test_nv21=format;set_gamma_mode(mode);struct test_context c=setup(argv[1],60);enqueue(&c);stream_on(&c);
  struct v4l2_plane p={};struct v4l2_buffer b=dequeue(c.fd,capture_type,&c.s,&p);
  assert(b.index==0 && b.sequence==0 && b.timestamp.tv_sec==1060);
  struct v4l2_plane ip={};dequeue(c.fd,output_type,&c.s,&ip);
  assert(crc32(c.in.address,bytes)==c.s.result[0].input_crc);
  unsigned ydiff=0;unsigned char *out=c.out.address;uint64_t ysum=0;
  for(unsigned y=0;y<480;y++)for(unsigned x=0;x<640;x++){unsigned v=out[y*640+x];ydiff+=v!=luma(60,0,x,y);ysum+=v;}
  for(unsigned i=bytes;i<c.out.length;i++)assert(out[i]==0xa7);
  uint32_t output_crc=crc32(out,bytes);dump_chain_file(argv[2],format,mode,"output",out,bytes);
  if(!mode)dump_chain_file(argv[2],format,mode,"input",c.in.address,bytes);
  unsigned pairdiff=0;if(mode==1)memcpy(pair,out,bytes);if(mode==2)for(unsigned i=0;i<bytes;i++)pairdiff+=pair[i]!=out[i];
  stream_off(&c,0);close_context(&c);snapshot(after,sizeof(after));
  printf("{\"format\":%u,\"mode\":%u,\"y_different\":%u,\"y_sum\":%llu,\"pair_identity_different\":%u,\"output_crc\":%u,\"after\":%s,\"completed\":true}\n",format,mode,ydiff,(unsigned long long)ysum,pairdiff,output_crc,after);fflush(stdout);
  if(!mode)assert(!ydiff);
  /* Identity quantization is analyzed on the host; no assumed exact equality. */
  assert(!metric(after,"failed") && !metric(after,"cancelled") && !metric(after,"first_error"));
 }
 free(pair);set_gamma_mode(0);snapshot(after,sizeof(after));assert(metric(after,"completed")==metric(before,"completed")+20 && metric(after,"direct_completed")==metric(after,"completed") && !metric(after,"users"));
 printf("{\"case\":\"fixed-gamma-chain\",\"frames\":20,\"before\":%s,\"after\":%s,\"passed\":true}\n",before,after);fflush(stdout);return 0;
}
