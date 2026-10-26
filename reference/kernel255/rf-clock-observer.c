/* Fixed read-only LOC supported-message query and RF/clock subscription.
 * Does not start/stop GNSS, set RF gain, change power, NV or calibration.
 * It unregisters only its own socket on exit. Raw stdout must stay private. */
#define main previous_readonly_main
#include "../kernel252/loc-readonly.c"
#undef main
#include <signal.h>
static volatile sig_atomic_t running=1;
static void stop(int sig){(void)sig;running=0;}
static void put16(uint8_t*p,uint16_t x){x=htole16(x);memcpy(p,&x,2);}
static int ack_ok(const uint8_t*b,size_t n){
 for(size_t p=7;p+3<=n;){uint16_t len=u16(b+p+1);if(p+3+len>n)return 0;
  if(b[p]==2&&len==4)return !u16(b+p+3)&&!u16(b+p+5);p+=3+len;}
 return 0;
}
static int request(int fd,struct qrtr_addr target,uint16_t txn,uint16_t id,const uint8_t*data,uint16_t size){
 uint8_t b[65536],req[32]={0};struct qrtr_addr peer;
 if(size>sizeof(req)-7)return 0;
 put16(req+1,txn);put16(req+3,id);put16(req+5,size);if(size)memcpy(req+7,data,size);
 if(sendto(fd,req,size+7,0,(void*)&target,sizeof(target))!=size+7)return 0;
 log_packet("request",req,size+7);
 double end=now()+5;
 while(running&&now()<end){
  ssize_t n=receive(fd,b,sizeof(b),&peer,200);if(n<0&&errno==EINTR)continue;if(n<0)return 0;if(!n)continue;
  if(peer.node!=target.node||peer.port!=target.port)continue;
  log_packet("reply",b,n);
  if(n>=7&&b[0]==2&&u16(b+1)==txn&&u16(b+3)==id&&u16(b+5)==n-7)return ack_ok(b,n);
 }
 return 0;
}
int main(int argc,char**argv){
 (void)argv;if(argc!=1)return 1;
 signal(SIGINT,stop);signal(SIGTERM,stop);
 int fd=socket(42,SOCK_DGRAM|SOCK_CLOEXEC,0);if(fd<0)return 2;
 struct qrtr_addr local={0},target={0},peer;socklen_t len=sizeof(local);
 if(getsockname(fd,(void*)&local,&len)){close(fd);return 3;}local.port=0;
 if(bind(fd,(void*)&local,sizeof(local))){close(fd);return 4;}
 struct qrtr_addr ns={.family=42,.node=local.node,.port=0xfffffffe};uint32_t lookup[5]={htole32(10),htole32(16),0,0,0};uint8_t b[65536];
 if(sendto(fd,lookup,sizeof(lookup),0,(void*)&ns,sizeof(ns))!=sizeof(lookup)){close(fd);return 5;}
 int candidates=0;double end=now()+3;
 while(running&&now()<end){ssize_t n=receive(fd,b,sizeof(b),&peer,200);if(n<0){close(fd);return 6;}
  if(n==20&&peer.port==0xfffffffe&&u32(b)==4&&u32(b+4)==16&&(u32(b+8)&255)==2){
   struct qrtr_addr p={.family=42,.node=u32(b+12),.port=u32(b+16)};
   if(!target.family){target=p;candidates++;}else if(target.node!=p.node||target.port!=p.port)candidates++;
  }
 }
 if(candidates!=1){close(fd);return 7;}
 int supported=request(fd,target,1,0x1e,NULL,0);
 printf("{\"kind\":\"supported_query_ack\",\"success\":%s}\n",supported?"true":"false");fflush(stdout);
 /* Official IDL event masks: BandMeasurementMetrics, GNSS measurements,
  * position, SV and NMEA. No RF configuration SET is included. */
 uint8_t mask[11]={1,8,0};uint64_t value=htole64(UINT64_C(0x40001000007));memcpy(mask+3,&value,8);
 int registered=request(fd,target,2,0x21,mask,sizeof(mask));
 printf("{\"kind\":\"registered\",\"success\":%s}\n",registered?"true":"false");fflush(stdout);
 if(!registered){close(fd);return 8;}
 end=now()+75;unsigned packets=0;
 while(running&&now()<end){ssize_t n=receive(fd,b,sizeof(b),&peer,250);if(n<0&&errno==EINTR)continue;if(n<0)break;if(!n)continue;
  if(peer.node!=target.node||peer.port!=target.port)continue;
  log_packet("indication",b,n);packets++;
 }
 running=1;memset(mask+3,0,8);
 int unregistered=request(fd,target,3,0x21,mask,sizeof(mask));close(fd);
 printf("{\"kind\":\"cleanup\",\"packets\":%u,\"registered\":true,\"unregister_ack_success\":%s,\"closed\":true}\n",packets,unregistered?"true":"false");
 return unregistered?0:9;
}
