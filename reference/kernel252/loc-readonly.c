/* Bounded read-only LOC query client. Only discovery and the listed GETs.
 * Raw replies may contain server details; stdout must remain private. */
#define _GNU_SOURCE
#include <sys/socket.h>
#include <poll.h>
#include <unistd.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <time.h>
#include <endian.h>
struct qrtr_addr { sa_family_t family; uint32_t node,port; };
static double now(void) { struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+t.tv_nsec/1e9; }
static uint32_t u32(const uint8_t*p) { uint32_t x;memcpy(&x,p,4);return le32toh(x); }
static uint16_t u16(const uint8_t*p) { uint16_t x;memcpy(&x,p,2);return le16toh(x); }
static void log_packet(const char*kind,const uint8_t*b,size_t n) {
 printf("{\"kind\":\"%s\",\"bytes\":%zu,\"hex\":\"",kind,n);
 for(size_t i=0;i<n;i++){printf("%02x",b[i]);}
 puts("\"}");fflush(stdout);
}
static ssize_t receive(int fd,uint8_t*b,size_t n,struct qrtr_addr*peer,int ms) {
 struct pollfd p={fd,POLLIN,0};int rc=poll(&p,1,ms);if(rc<=0)return rc;
 struct iovec v={b,n};struct msghdr m={.msg_name=peer,.msg_namelen=sizeof(*peer),.msg_iov=&v,.msg_iovlen=1};
 ssize_t got=recvmsg(fd,&m,0);if(m.msg_flags&MSG_TRUNC){errno=EMSGSIZE;return -1;}return got;
}
int main(int argc,char **argv) {
 unsigned service=16,version=2;
 if(argc==2&&!strcmp(argv[1],"pdc")){service=36;version=1;}
 else if(argc==2&&!strcmp(argv[1],"dms")){service=2;version=1;}
 else if(argc==2&&!strcmp(argv[1],"controls")){service=16;version=2;}
 else if(argc!=1){fputs("Only fixed LOC, controls, pdc or dms GET suites are allowed\n",stderr);return 1;}
 int fd=socket(42,SOCK_DGRAM|SOCK_CLOEXEC,0);if(fd<0){perror("qrtr socket");return 2;}
 struct qrtr_addr local={.family=42,.node=0,.port=0};
 socklen_t alen=sizeof(local);
 if(getsockname(fd,(void*)&local,&alen)){perror("initial getsockname");close(fd);return 3;}
 local.port=0;
 if(bind(fd,(void*)&local,sizeof(local))){perror("bind");close(fd);return 3;}
 alen=sizeof(local);if(getsockname(fd,(void*)&local,&alen)){perror("getsockname");close(fd);return 4;}
 struct qrtr_addr ns={.family=42,.node=local.node,.port=0xfffffffe},target={0},peer;
 uint32_t lookup[5]={htole32(10),htole32(service),0,0,0};uint8_t buf[65536];
 if(sendto(fd,lookup,sizeof(lookup),0,(void*)&ns,sizeof(ns))!=sizeof(lookup)){perror("lookup");close(fd);return 5;}
 double end=now()+4;int candidates=0;
 while(now()<end) {
  ssize_t n=receive(fd,buf,sizeof(buf),&peer,250);if(n<0){perror("discover");close(fd);return 6;}if(!n)continue;
  log_packet("discovery",buf,(size_t)n);
  if(n==20&&peer.port==0xfffffffe&&u32(buf)==4&&u32(buf+4)==service&&(u32(buf+8)&255)==version) {
   struct qrtr_addr t={.family=42,.node=u32(buf+12),.port=u32(buf+16)};
   if(!target.family){target=t;candidates++;}else if(t.node!=target.node||t.port!=target.port)candidates++;
  }
 }
 if(candidates!=1){fprintf(stderr,"expected one service %u v%u endpoint, got %d\n",service,version,candidates);close(fd);return 7;}
 printf("{\"kind\":\"endpoint_selected\",\"service\":%u,\"version\":%u}\n",service,version);fflush(stdout);
 /* No event mask, engine start/stop, power, lock SET, or data injection. */
 const uint16_t ids[]={0x0037,0x0036,0x003b,0x004b,0x0033};
 /* Verified from the matching stock library's getBlacklistSv and
  * getConstellationControl closures, including APS2 vtable relocations. */
 const uint16_t controls[]={0x00b7,0x00bf};
 int control_suite=argc==2&&!strcmp(argv[1],"controls");
 size_t count=service==36?2:service==2?1:control_suite?2:sizeof(ids)/sizeof(ids[0]);
 for(size_t i=0;i<count;i++) {
  uint16_t txn=(uint16_t)(i+1),id=service==36?0x22:service==2?0x2d:control_suite?controls[i]:ids[i];
  uint8_t req[32]={0,txn&255,txn>>8,id&255,id>>8,0,0};size_t reqsize=7;
  if(service==36){
   /* PLATFORM=0, SOFTWARE=1; optional token correlates each completion. */
   req[5]=14;req[7]=1;req[8]=4;req[10]=(uint8_t)i;
   req[14]=0x10;req[15]=4;uint32_t token=htole32(25200+(uint32_t)i);memcpy(req+17,&token,4);reqsize=21;
  }
  if(sendto(fd,req,reqsize,0,(void*)&target,sizeof(target))!=(ssize_t)reqsize){perror("query");close(fd);return 8;}
  log_packet("request",req,reqsize);end=now()+4;int ack=0,ind=0;
  while(now()<end&&!(ack&&(ind||service==2))) {
   ssize_t n=receive(fd,buf,sizeof(buf),&peer,250);if(n<0){perror("receive");close(fd);return 9;}if(!n)continue;
   if(peer.node!=target.node||peer.port!=target.port)continue;
   log_packet("reply",buf,(size_t)n);
   if(n>=7&&u16(buf+3)==id&&u16(buf+5)==n-7) {
    if(buf[0]==2&&u16(buf+1)==txn)ack=1;
    if(buf[0]==4)ind=1;
   }
  }
  printf("{\"kind\":\"query_done\",\"message_id\":%u,\"ack\":%s,\"indication\":%s}\n",id,ack?"true":"false",ind?"true":"false");fflush(stdout);
 }
 close(fd);puts("{\"kind\":\"closed\",\"success\":true}");return 0;
}
