/* SPDX-License-Identifier: GPL-2.0-only */
/* Exercise the shared CSI stream through independent RDI and PIX consumers. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <linux/videodev2.h>
#include <poll.h>
#include <signal.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <unistd.h>
struct node {int fd;bool streaming;unsigned count,epoch,frames;uint32_t last;int64_t time;
 struct v4l2_format format;void *maps[4];size_t lengths[4];const char *name;};
static volatile sig_atomic_t interrupted;
static void stop_signal(int sig){(void)sig;interrupted=1;}
static int call(int fd,unsigned long op,void *arg){int r;do{r=ioctl(fd,op,arg);}while(r<0&&errno==EINTR&&!interrupted);if(r<0)fprintf(stderr,"IOCTL_FAILURE fd=%d op=%#lx errno=%d\n",fd,op,errno);return r;}
static int queue(struct node *n,unsigned index){
 struct v4l2_plane p={.length=n->lengths[index]};
 struct v4l2_buffer b={.type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE,.memory=V4L2_MEMORY_MMAP,.index=index,.length=1,.m.planes=&p};
 return call(n->fd,VIDIOC_QBUF,&b);
}
static int open_node(struct node *n,const char *path,unsigned width,unsigned height,uint32_t fourcc){
 n->fd=open(path,O_RDWR|O_NONBLOCK|O_CLOEXEC);if(n->fd<0)return -1;
 n->format=(struct v4l2_format){.type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE};
 struct v4l2_pix_format_mplane *f=&n->format.fmt.pix_mp;
 f->width=width;f->height=height;f->pixelformat=fourcc;f->field=V4L2_FIELD_NONE;
 if(call(n->fd,VIDIOC_S_FMT,&n->format))return -1;
 printf("FORMAT node=%s width=%u height=%u fourcc=%#x planes=%u stride=%u bytes=%u\n",n->name,f->width,f->height,f->pixelformat,f->num_planes,f->plane_fmt[0].bytesperline,f->plane_fmt[0].sizeimage);
 if(f->width!=width||f->height!=height||f->pixelformat!=fourcc||f->num_planes!=1){errno=EPROTO;return -1;}
 struct v4l2_requestbuffers req={.type=n->format.type,.memory=V4L2_MEMORY_MMAP,.count=4};
 if(call(n->fd,VIDIOC_REQBUFS,&req)||req.count!=4)return -1;
 n->count=req.count;
 for(unsigned i=0;i<n->count;i++){
  struct v4l2_plane p={0};struct v4l2_buffer b={.type=n->format.type,.memory=V4L2_MEMORY_MMAP,.index=i,.length=1,.m.planes=&p};
  if(call(n->fd,VIDIOC_QUERYBUF,&b))return -1;
  n->lengths[i]=p.length;n->maps[i]=mmap(NULL,p.length,PROT_READ|PROT_WRITE,MAP_SHARED,n->fd,p.m.mem_offset);
  if(n->maps[i]==MAP_FAILED){n->maps[i]=NULL;return -1;}
  memset(n->maps[i],0xa5,p.length);
 }
 return 0;
}
static int start(struct node *n){
 for(unsigned i=0;i<n->count;i++)if(queue(n,i))return -1;
 if(call(n->fd,VIDIOC_STREAMON,&n->format.type))return -1;
 n->streaming=true;n->frames=0;n->last=0;n->time=0;++n->epoch;
 printf("START node=%s epoch=%u\n",n->name,n->epoch);fflush(stdout);return 0;
}
static int stop(struct node *n){
 if(!n->streaming)return 0;
 int r=call(n->fd,VIDIOC_STREAMOFF,&n->format.type);n->streaming=false;
 printf("STOP node=%s epoch=%u result=%d\n",n->name,n->epoch,r);fflush(stdout);return r;
}
static int capture(struct node nodes[2],unsigned phase){
 unsigned frames[2]={0};
 while(!interrupted){
  bool done=true;struct pollfd fds[2];
  for(unsigned i=0;i<2;i++){fds[i]=(struct pollfd){.fd=nodes[i].streaming?nodes[i].fd:-1,.events=POLLIN};if(nodes[i].streaming&&frames[i]<8)done=false;}
  if(done)return 0;
  if(poll(fds,2,3000)<=0){errno=ETIMEDOUT;return -1;}
  for(unsigned i=0;i<2;i++)if(fds[i].revents&POLLIN){
   struct node *n=&nodes[i];struct v4l2_plane p={0};
   struct v4l2_buffer b={.type=n->format.type,.memory=V4L2_MEMORY_MMAP,.length=1,.m.planes=&p};
   if(call(n->fd,VIDIOC_DQBUF,&b))return -1;
   if(b.index>=n->count||b.flags&V4L2_BUF_FLAG_ERROR||p.bytesused!=n->format.fmt.pix_mp.plane_fmt[0].sizeimage||p.bytesused>n->lengths[b.index]){errno=EIO;return -1;}
   int64_t time=(int64_t)b.timestamp.tv_sec*1000000+b.timestamp.tv_usec;
   if(time<=0||(n->frames&&(b.sequence<=n->last||time<=n->time))){errno=EPROTO;return -1;}
   unsigned changed=0;uint64_t hash=UINT64_C(14695981039346656037);
   for(unsigned y=0;y<16;y++)for(unsigned x=0;x<128;x++){
    unsigned char value=((unsigned char*)n->maps[b.index])[(size_t)y*n->format.fmt.pix_mp.plane_fmt[0].bytesperline+x];
    changed+=value!=0xa5;hash=(hash^value)*UINT64_C(1099511628211);
   }
   if(changed<1536){errno=ENODATA;return -1;}
   printf("DUAL_FRAME phase=%u node=%s epoch=%u sequence=%u timestamp_us=%" PRId64 " bytes=%u changed=%u hash=%016" PRIx64 "\n",phase,n->name,n->epoch,b.sequence,time,p.bytesused,changed,hash);fflush(stdout);
   n->last=b.sequence;n->time=time;++n->frames;++frames[i];
   if(queue(n,b.index))return -1;
  }
 }
 errno=EINTR;return -1;
}
int main(int argc,char **argv){
 if(argc!=7)return 2;
 signal(SIGINT,stop_signal);signal(SIGTERM,stop_signal);
 printf("APPLICATION_PROCESS pid=%d\n",getpid());
 struct node nodes[2]={{.fd=-1,.name="raw"},{.fd=-1,.name="pix"}};
 unsigned w=strtoul(argv[3],NULL,10),h=strtoul(argv[4],NULL,10);int result=1;
 uint32_t raw=!strcmp(argv[5],"GBRG")?V4L2_PIX_FMT_SGBRG10P:!strcmp(argv[5],"GRBG")?V4L2_PIX_FMT_SGRBG10P:V4L2_PIX_FMT_SRGGB10P;
 unsigned first=!strcmp(argv[6],"pix-first");
 if(open_node(&nodes[0],argv[1],w,h,raw)||open_node(&nodes[1],argv[2],640,480,V4L2_PIX_FMT_NV12))goto cleanup;
 if(start(&nodes[first])||start(&nodes[1-first])||capture(nodes,0))goto cleanup;
 if(stop(&nodes[0])||capture(nodes,1))goto cleanup;
 if(start(&nodes[0])||capture(nodes,2))goto cleanup;
 if(stop(&nodes[1])||capture(nodes,3))goto cleanup;
 if(start(&nodes[1])||capture(nodes,4))goto cleanup;
 result=0;
cleanup:
 if(result)fprintf(stderr,"DUAL_FAILURE errno=%d reason=%s\n",errno,strerror(errno));
 for(unsigned i=0;i<2;i++)if(stop(&nodes[i]))result=1;
 for(unsigned i=0;i<2;i++){
  struct node *n=&nodes[i];for(unsigned b=0;b<n->count;b++)if(n->maps[b])munmap(n->maps[b],n->lengths[b]);
  if(n->fd>=0){struct v4l2_requestbuffers req={.type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE,.memory=V4L2_MEMORY_MMAP};if(call(n->fd,VIDIOC_REQBUFS,&req))result=1;close(n->fd);}
 }
 printf("DUAL_RESULT success=%u\n",!result);return result;
}
