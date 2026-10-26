/* Same-device comparison of the basic Linux LOC path on the stock kernel.
 * Fixed REGISTER / per-client STANDALONE / HIGH START / STOP sequence.
 * No DMS power changes, lock/constellation changes, NV or calibration writes. */
#define main readonly_program_main
#include "loc-readonly.c"
#undef main
#include <signal.h>
static volatile sig_atomic_t quit;
static int session_fd=-1;
static struct qrtr_addr session_peer;
static uint16_t sequence;
static void stop_signal(int sig){(void)sig;quit=1;}
static void put16(uint8_t*p,uint16_t v){v=htole16(v);memcpy(p,&v,2);}
static size_t tlv(uint8_t*p,uint8_t tag,const void*data,uint16_t size){p[0]=tag;put16(p+1,size);memcpy(p+3,data,size);return size+3;}
static int ack_ok(const uint8_t*b,size_t n){
 for(size_t p=7;p+3<=n;){uint16_t len=u16(b+p+1);if(p+3+len>n)return 0;if(b[p]==2&&len==4)return u16(b+p+3)==0&&u16(b+p+5)==0;p+=3+len;}
 return 0;
}
static int exchange(uint16_t id,const uint8_t*payload,size_t length,int completion){
 uint8_t req[128]={0};uint8_t buf[65536];struct qrtr_addr peer;
 if(length>sizeof(req)-7)return 0;
 uint16_t txn=++sequence;put16(req+1,txn);put16(req+3,id);put16(req+5,(uint16_t)length);if(length)memcpy(req+7,payload,length);
 if(sendto(session_fd,req,7+length,0,(void*)&session_peer,sizeof(session_peer))!=(ssize_t)(7+length))return 0;
 log_packet("request",req,7+length);int ack=0,ind=0;double end=now()+4;
 while(now()<end&&!(ack&&(!completion||ind))){
  ssize_t n=receive(session_fd,buf,sizeof(buf),&peer,200);if(n<0)return 0;if(!n)continue;
  if(peer.node!=session_peer.node||peer.port!=session_peer.port)continue;
  log_packet("reply",buf,(size_t)n);
  if(n<7||u16(buf+5)!=(size_t)n-7||u16(buf+3)!=id)continue;
  if(buf[0]==2&&u16(buf+1)==txn){if(!ack_ok(buf,(size_t)n))return 0;ack=1;}
  if(buf[0]==4){if(n<14||buf[7]!=1||u16(buf+8)!=4||u32(buf+10)!=0)return 0;ind=1;}
 }
 return ack&&(!completion||ind);
}
int main(void){
 signal(SIGINT,stop_signal);signal(SIGTERM,stop_signal);
 session_fd=socket(42,SOCK_DGRAM|SOCK_CLOEXEC,0);if(session_fd<0){perror("socket");return 2;}
 struct qrtr_addr local={0},peer; socklen_t len=sizeof(local);
 if(getsockname(session_fd,(void*)&local,&len)){perror("getsockname");close(session_fd);return 3;}
 local.port=0;if(bind(session_fd,(void*)&local,sizeof(local))){perror("bind");close(session_fd);return 4;}
 struct qrtr_addr ns={.family=42,.node=local.node,.port=0xfffffffe};
 uint32_t lookup[5]={htole32(10),htole32(16),0,0,0};uint8_t buf[65536];int candidates=0;
 if(sendto(session_fd,lookup,sizeof(lookup),0,(void*)&ns,sizeof(ns))!=sizeof(lookup)){close(session_fd);return 5;}
 double end=now()+4;
 while(now()<end&&!quit){
  ssize_t n=receive(session_fd,buf,sizeof(buf),&peer,200);if(n<0){close(session_fd);return 6;}if(!n)continue;
  if(n==20&&peer.port==0xfffffffe&&u32(buf)==4&&u32(buf+4)==16&&(u32(buf+8)&255)==2){
   struct qrtr_addr p={.family=42,.node=u32(buf+12),.port=u32(buf+16)};
   if(!session_peer.family){session_peer=p;candidates++;}else if(p.node!=session_peer.node||p.port!=session_peer.port)candidates++;
  }
 }
 if(candidates!=1||quit){close(session_fd);return 7;}
 uint8_t payload[64];size_t size=0;uint64_t mask=htole64(7);uint32_t mode=htole32(4);uint8_t sid=252;
 size=tlv(payload,1,&mask,8);
 int registered=exchange(0x21,payload,size,0),mode_ok=0,start_ok=0,attempted=0,stop_ok=0;
 if(!registered||quit)goto cleanup;
 size=tlv(payload,1,&mode,4);mode_ok=exchange(0x4a,payload,size,1);if(!mode_ok||quit)goto cleanup;
 size=tlv(payload,1,&sid,1);
 uint32_t recurrence=htole32(1),high=htole32(3),intermediate=htole32(2),interval=htole32(1000);
 size+=tlv(payload+size,16,&recurrence,4);size+=tlv(payload+size,17,&high,4);size+=tlv(payload+size,18,&intermediate,4);size+=tlv(payload+size,19,&interval,4);
 attempted=1;start_ok=exchange(0x22,payload,size,0);if(!start_ok||quit)goto cleanup;
 puts("{\"kind\":\"phase\",\"phase\":\"stock_native_standalone_high\",\"seconds\":90}");fflush(stdout);
 double began=now();end=began+90;unsigned records=0;
 while(now()<end&&!quit){
  ssize_t n=receive(session_fd,buf,sizeof(buf),&peer,200);if(n<0)break;if(!n)continue;
  if(peer.node!=session_peer.node||peer.port!=session_peer.port)continue;
  log_packet("reply",buf,(size_t)n);if(++records>10000)break;
 }
 printf("{\"kind\":\"observation_end\",\"elapsed_seconds\":%.3f,\"records\":%u}\n",now()-began,records);fflush(stdout);
cleanup:
 if(attempted){size=tlv(payload,1,&sid,1);stop_ok=exchange(0x23,payload,size,0);}
 mask=0;size=tlv(payload,1,&mask,8);int unregistered=registered?exchange(0x21,payload,size,0):1;
 close(session_fd);
 printf("{\"kind\":\"cleanup\",\"registered\":%s,\"mode_ack_and_completion\":%s,\"start_ack\":%s,\"stop_ack\":%s,\"unregistered\":%s,\"closed\":true,\"interrupted\":%s}\n",registered?"true":"false",mode_ok?"true":"false",start_ok?"true":"false",stop_ok?"true":"false",unregistered?"true":"false",quit?"true":"false");
 return registered&&mode_ok&&start_ok&&stop_ok&&unregistered&&!quit?0:1;
}
