/* Fixed GET SBAS / UTC assistance diagnostic. UTC injection adjusts only
 * normal positioning assistance: no system clock, NV, RF or calibration SET.
 * Reference UTC is externally verified; raw replies must remain private. */
#define main previous_readonly_main
#include "../kernel252/loc-readonly.c"
#undef main
#include <inttypes.h>
static void put16(uint8_t*p,uint16_t v){v=htole16(v);memcpy(p,&v,2);}
static uint64_t boot_ms(void){struct timespec t;if(clock_gettime(CLOCK_BOOTTIME,&t))return 0;return (uint64_t)t.tv_sec*1000+t.tv_nsec/1000000;}
static int result_ok(const uint8_t*b,size_t n){for(size_t p=7;p+3<=n;){uint16_t len=u16(b+p+1);if(p+3+len>n)return 0;if(b[p]==2&&len==4)return !u16(b+p+3)&&!u16(b+p+5);p+=3+len;}return 0;}
static int completion_ok(const uint8_t*b,size_t n){return n>=14&&b[7]==1&&u16(b+8)==4&&!u32(b+10);}
static int execute(int fd,struct qrtr_addr target,uint16_t id,const uint8_t*payload,uint16_t size){
 uint8_t req[128]={0},b[65536];struct qrtr_addr peer;
 if(size>sizeof(req)-7)return 0;
 put16(req+1,1);put16(req+3,id);put16(req+5,size);if(size)memcpy(req+7,payload,size);
 if(sendto(fd,req,7+size,0,(void*)&target,sizeof(target))!=7+size)return 0;
 log_packet("request",req,7+size);double end=now()+5;int ack=0,done=0;
 while(now()<end&&!(ack&&done)){
  ssize_t n=receive(fd,b,sizeof(b),&peer,200);if(n<0)return 0;if(!n)continue;
  if(peer.node!=target.node||peer.port!=target.port)continue;
  log_packet("reply",b,n);
  if(n<7||u16(b+3)!=id||u16(b+5)!=n-7)continue;
  if(b[0]==2&&u16(b+1)==1){if(!result_ok(b,n))return 0;ack=1;}
  if(b[0]==4){if(!completion_ok(b,n))return 0;done=1;}
 }
 return ack&&done;
}
int main(int argc,char**argv){
 int inject=argc==5&&!strcmp(argv[1],"inject-utc");
 if(!inject&&!(argc==2&&!strcmp(argv[1],"get-sbas"))){fputs("get-sbas OR inject-utc reference_boot_ms reference_utc_ms uncertainty_ms\n",stderr);return 1;}
 uint64_t reference_boot=0,reference_utc=0,unc=0;
 if(inject){char*e;errno=0;reference_boot=strtoull(argv[2],&e,10);if(errno||*e)return 1;reference_utc=strtoull(argv[3],&e,10);if(errno||*e)return 1;unc=strtoull(argv[4],&e,10);if(errno||*e||unc<1||unc>10000||reference_utc<1577836800000ULL||reference_utc>2208988800000ULL)return 1;}
 int fd=socket(42,SOCK_DGRAM|SOCK_CLOEXEC,0);if(fd<0)return 2;
 struct qrtr_addr local={0},target={0},peer; socklen_t len=sizeof(local);
 if(getsockname(fd,(void*)&local,&len)){close(fd);return 3;}local.port=0;
 if(bind(fd,(void*)&local,sizeof(local))){close(fd);return 4;}
 struct qrtr_addr ns={.family=42,.node=local.node,.port=0xfffffffe};uint32_t lookup[5]={htole32(10),htole32(16),0,0,0};uint8_t b[65536];
 if(sendto(fd,lookup,sizeof(lookup),0,(void*)&ns,sizeof(ns))!=sizeof(lookup)){close(fd);return 5;}
 double end=now()+2;int candidates=0;
 while(now()<end){ssize_t n=receive(fd,b,sizeof(b),&peer,200);if(n<0){close(fd);return 6;}if(n==20&&peer.port==0xfffffffe&&u32(b)==4&&u32(b+4)==16&&(u32(b+8)&255)==2){struct qrtr_addr p={.family=42,.node=u32(b+12),.port=u32(b+16)};if(!target.family){target=p;candidates++;}else if(target.node!=p.node||target.port!=p.port)candidates++;}}
 if(candidates!=1){close(fd);return 7;}
 uint16_t id=inject?0x38:0x3d;uint8_t payload[18];uint16_t size=0;
 if(inject){uint64_t current=boot_ms();if(current<reference_boot||current-reference_boot>120000){close(fd);return 8;}uint64_t utc=htole64(reference_utc+current-reference_boot);uint32_t uncertainty=htole32(unc);payload[0]=1;put16(payload+1,8);memcpy(payload+3,&utc,8);payload[11]=2;put16(payload+12,4);memcpy(payload+14,&uncertainty,4);size=18;printf("{\"kind\":\"injection_parameters\",\"reference_age_ms\":%"PRIu64",\"uncertainty_ms\":%"PRIu64"}\n",current-reference_boot,unc);}
 int ok=execute(fd,target,id,payload,size);close(fd);
 printf("{\"kind\":\"cleanup\",\"ack_and_completion_success\":%s,\"closed\":true}\n",ok?"true":"false");return ok?0:9;
}
