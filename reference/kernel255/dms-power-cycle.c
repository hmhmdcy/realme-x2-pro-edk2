/* Bounded ONLINE -> temporary LOW_POWER -> ONLINE observation.
 * Only DMS GET 0x2d and SET 0x2e modes 0/1. Requires initial ONLINE.
 * No OFFLINE, RESET, factory-test, persistent mode, NV or calibration API.
 * The host must verify same device/boot, absent SIMs and idle calls first.
 * Raw stdout includes replies and must stay private. */
#define main previous_readonly_main
#include "../kernel252/loc-readonly.c"
#undef main
#include <signal.h>
static volatile sig_atomic_t running=1;
static unsigned txn=0;
static void stop(int sig){(void)sig;running=0;}
static void put16(uint8_t*p,uint16_t x){x=htole16(x);memcpy(p,&x,2);}
static int transact(int fd,struct qrtr_addr target,int set,int value){
 uint8_t req[16]={0},b[65536];struct qrtr_addr peer;uint16_t id=set?0x2e:0x2d;txn++;
 put16(req+1,txn);put16(req+3,id);
 size_t size=7;if(set){put16(req+5,4);req[7]=1;req[8]=1;req[10]=(uint8_t)value;size=11;}
 if(sendto(fd,req,size,0,(void*)&target,sizeof(target))!=(ssize_t)size)return -1;
 log_packet("request",req,size);double end=now()+5;
 while(now()<end){ssize_t n=receive(fd,b,sizeof(b),&peer,200);if(n<0&&errno==EINTR)continue;if(n<0)return -1;if(!n)continue;
  if(peer.node!=target.node||peer.port!=target.port)continue;log_packet("reply",b,n);
  if(n<7||b[0]!=2||u16(b+1)!=txn||u16(b+3)!=id||u16(b+5)!=n-7)continue;
  int ok=0,mode=-1;
  for(size_t p=7;p+3<=(size_t)n;){uint16_t len=u16(b+p+1);if(p+3+len>(size_t)n)return -1;
   if(b[p]==2&&len==4)ok=!u16(b+p+3)&&!u16(b+p+5);
   if(b[p]==1&&len==1)mode=b[p+3];p+=3+len;
  }
  return ok?(set?value:mode):-1;
 }
 return -1;
}
static int observe(int fd,struct qrtr_addr target,int seconds,const char*label){
 double end=now()+seconds;int samples=0;
 printf("{\"kind\":\"phase\",\"phase\":\"%s\",\"monotonic\":%.6f}\n",label,now());fflush(stdout);
 while(running&&now()<end){int mode=transact(fd,target,0,0);
  printf("{\"kind\":\"mode_sample\",\"phase\":\"%s\",\"mode\":%d,\"monotonic\":%.6f}\n",label,mode,now());fflush(stdout);samples++;
  struct timespec t={1,0};nanosleep(&t,NULL);
 }
 return samples;
}
int main(int argc,char**argv){
 (void)argv;if(argc!=1)return 1;signal(SIGINT,stop);signal(SIGTERM,stop);
 int fd=socket(42,SOCK_DGRAM|SOCK_CLOEXEC,0);if(fd<0)return 2;
 struct qrtr_addr local={0},target={0},peer;socklen_t len=sizeof(local);
 if(getsockname(fd,(void*)&local,&len)){close(fd);return 3;}local.port=0;
 if(bind(fd,(void*)&local,sizeof(local))){close(fd);return 4;}
 struct qrtr_addr ns={.family=42,.node=local.node,.port=0xfffffffe};uint32_t lookup[5]={htole32(10),htole32(2),0,0,0};uint8_t b[65536];
 if(sendto(fd,lookup,sizeof(lookup),0,(void*)&ns,sizeof(ns))!=sizeof(lookup)){close(fd);return 5;}
 int candidates=0;double end=now()+3;
 while(running&&now()<end){ssize_t n=receive(fd,b,sizeof(b),&peer,200);if(n<0){close(fd);return 6;}
  if(n==20&&peer.port==0xfffffffe&&u32(b)==4&&u32(b+4)==2&&(u32(b+8)&255)==1){struct qrtr_addr p={.family=42,.node=u32(b+12),.port=u32(b+16)};
   if(!target.family){target=p;candidates++;}else if(target.node!=p.node||target.port!=p.port)candidates++;
  }
 }
 if(candidates!=1){close(fd);return 7;}
 int initial=transact(fd,target,0,0);
 printf("{\"kind\":\"initial\",\"mode\":%d}\n",initial);fflush(stdout);
 if(initial!=0){close(fd);return 8;}
 observe(fd,target,20,"A1_online");
 if(!running){close(fd);return 9;}
 int low=transact(fd,target,1,1);
 printf("{\"kind\":\"set_low_power_ack\",\"success\":%s}\n",low==1?"true":"false");fflush(stdout);
 if(low==1)observe(fd,target,30,"B_low_power_requested");
 int online=transact(fd,target,1,0);
 printf("{\"kind\":\"restore_online_ack\",\"success\":%s}\n",online==0?"true":"false");fflush(stdout);
 if(online==0&&running)observe(fd,target,35,"A2_online_restored");
 int final=transact(fd,target,0,0);close(fd);
 printf("{\"kind\":\"cleanup\",\"initial_mode\":%d,\"final_mode\":%d,\"online_restore_ack\":%s,\"closed\":true}\n",initial,final,online==0?"true":"false");
 return online==0&&final==0?0:10;
}
