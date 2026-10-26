/* SPDX-License-Identifier: GPL-2.0-only */
#define _GNU_SOURCE
#include <assert.h>
#include <fcntl.h>
#include <linux/dma-buf.h>
#include <linux/videodev2.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <time.h>
#include <unistd.h>
static volatile sig_atomic_t interrupted;
static void stop(int sig){(void)sig;interrupted=1;}
static void call(int fd,unsigned long request,void *arg){assert(!ioctl(fd,request,arg));}
static void marker(const char *root,const char *name){char path[512];assert(snprintf(path,sizeof(path),"%s/%s",root,name)<(int)sizeof(path));int fd=open(path,O_CREAT|O_EXCL|O_WRONLY|O_CLOEXEC,0600);assert(fd>=0);assert(write(fd,"1\n",2)==2);assert(!fsync(fd));close(fd);}
static bool wait_marker(const char *root,const char *name){char path[512];assert(snprintf(path,sizeof(path),"%s/%s",root,name)<(int)sizeof(path));for(unsigned i=0;i<2000 && !interrupted;++i){if(!access(path,F_OK))return true;usleep(10000);}return false;}
int main(int argc,char **argv){
 if(argc!=3)return 2;signal(SIGTERM,stop);signal(SIGINT,stop);
 int video=open(argv[1],O_RDWR|O_NONBLOCK|O_CLOEXEC);assert(video>=0);
 struct v4l2_format format={.type=V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE};
 format.fmt.pix_mp.width=640;format.fmt.pix_mp.height=480;format.fmt.pix_mp.pixelformat=V4L2_PIX_FMT_NV12;format.fmt.pix_mp.field=V4L2_FIELD_NONE;call(video,VIDIOC_S_FMT,&format);
 struct v4l2_requestbuffers req={.count=1,.type=V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE,.memory=V4L2_MEMORY_MMAP};call(video,VIDIOC_REQBUFS,&req);assert(req.count);
 struct v4l2_exportbuffer exp={.type=V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE,.index=0,.plane=0,.flags=O_RDWR|O_CLOEXEC};call(video,VIDIOC_EXPBUF,&exp);
 size_t bytes=format.fmt.pix_mp.plane_fmt[0].sizeimage;
 unsigned char *map=mmap(NULL,bytes,PROT_READ|PROT_WRITE,MAP_SHARED,exp.fd,0);assert(map!=MAP_FAILED);
 struct dma_buf_sync sync={DMA_BUF_SYNC_START|DMA_BUF_SYNC_WRITE};call(exp.fd,DMA_BUF_IOCTL_SYNC,&sync);memset(map,0x5b,bytes);sync.flags=DMA_BUF_SYNC_END|DMA_BUF_SYNC_WRITE;call(exp.fd,DMA_BUF_IOCTL_SYNC,&sync);
 close(video);marker(argv[2],"export-held");bool good=wait_marker(argv[2],"close-export-fd");
 close(exp.fd);marker(argv[2],"mmap-only-held");good=good && wait_marker(argv[2],"release-export-mmap");
 for(size_t i=0;i<bytes;++i)assert(map[i]==0x5b);
 assert(!munmap(map,bytes));marker(argv[2],"export-released");
 printf("EXPORT_LIFETIME bytes=%zu fd_closed_before_munmap=1 result=%d\n",bytes,!good);return good?0:3;
}
