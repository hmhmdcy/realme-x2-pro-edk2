#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
typedef uint32_t u32;
typedef uint32_t __le32;
#define CAMSS_A5_QUEUE_COUNT 3
#define CAMSS_A5_QUEUE_SLOTS 4
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define READ_ONCE(x) (x)
#define le32_to_cpu(x) (x)
#define cpu_to_le32(x) (x)
#define min_t(type,a,b) ((type)(a)<(type)(b)?(type)(a):(type)(b))
#define GFP_KERNEL 0
#define SFR_OFFSET 0x1c000U
static void dma_rmb(void) {}
static u32 get_unaligned_le32(const void *p) {u32 value;memcpy(&value,p,4);return value;}
#include "queue-types.inc"
struct camss_a5 {
 void *dev;
 struct {void *cpu;u32 bytes;} shared;
 struct camss_a5_qtable *table;
 u32 queue_state[6],init_response,fw_version,interrupts,watchdogs,protocol_errors;
 char sfr[512];bool cpu_release_attempted;
};
static void *retained;
static size_t retained_bytes;
static unsigned dumps,allocations;
static bool fail_allocation;
static void *vzalloc(size_t bytes) {++allocations;return fail_allocation?NULL:calloc(1,bytes);}
static void dev_coredumpv(void *dev,void *data,size_t bytes,int flags) {
 (void)flags;assert(dev==(void *)1 && !retained);retained=data;retained_bytes=bytes;++dumps;
}
#include "diagnostic-methods.inc"
int main(int argc,char **argv)
{
 struct camss_a5 a={.dev=(void *)1,.init_response=3,.fw_version=0x01000100,.interrupts=9,.watchdogs=2,.protocol_errors=7};
 _Static_assert(sizeof(struct camss_a5_start_dump)==568,"bounded diagnostic format");
 _Static_assert(sizeof(struct camss_a5_qtable)==3848,"real production queue ABI");
 size_t capacity=SFR_OFFSET+1024;a.shared.cpu=malloc(capacity);assert(a.shared.cpu);a.shared.bytes=capacity;a.table=a.shared.cpu;memset(a.shared.cpu,0,capacity);
 for(unsigned i=0;i<CAMSS_A5_QUEUE_COUNT;i++){a.table->queues[i].read=10+i;a.table->queues[i].write=20+i;}
 u32 declared=4096;memcpy(a.shared.cpu+SFR_OFFSET,&declared,4);memset(a.shared.cpu+SFR_OFFSET+4,'F',1020);
 publish_start_failure(&a);assert(!dumps && !allocations);
 a.cpu_release_attempted=true;publish_start_failure(&a);assert(dumps==1 && retained_bytes==568);
 struct camss_a5_start_dump *dump=retained;assert(!memcmp(dump->magic,"CAMSSA5\0",8) && dump->version==1 && dump->init_response==3 && dump->fw_version==0x01000100);
 assert(dump->interrupts==9 && dump->watchdogs==2 && dump->protocol_errors==7);
 for(unsigned i=0;i<CAMSS_A5_QUEUE_COUNT;i++){assert(dump->queue_state[i*2]==10+i);assert(dump->queue_state[i*2+1]==20+i);}
 for(unsigned i=0;i<511;i++)assert(dump->sfr[i]=='F');assert(!dump->sfr[511]);
 if(argc==2){FILE *out=fopen(argv[1],"wb");assert(out);assert(fwrite(retained,1,retained_bytes,out)==retained_bytes);assert(fclose(out)==0);}
 memset(a.shared.cpu,0,capacity);assert(dump->sfr[0]=='F');free(retained);retained=NULL;
 fail_allocation=true;publish_start_failure(&a);assert(dumps==1 && allocations==2);fail_allocation=false;
 /* A partial SFR allocation bounds copying even when the header is corrupt. */
 for(unsigned extra=0;extra<=9;extra++){
  a.shared.bytes=SFR_OFFSET+extra;declared=UINT32_MAX;memcpy(a.shared.cpu+SFR_OFFSET,&declared,4);memset(a.shared.cpu+SFR_OFFSET+4,'Z',16);
  capture_shared_state(&a);unsigned wanted=extra>4?extra-4:0;
  for(unsigned i=0;i<wanted;i++)assert(a.sfr[i]=='Z');for(unsigned i=wanted;i<512;i++)assert(a.sfr[i]==0);
 }
 a.shared.bytes=capacity;
 for(declared=0;declared<=6;declared++){
  memcpy(a.shared.cpu+SFR_OFFSET,&declared,4);capture_shared_state(&a);unsigned wanted=declared>4?declared-4:0;
  for(unsigned i=0;i<wanted;i++)assert(a.sfr[i]=='Z');for(unsigned i=wanted;i<512;i++)assert(a.sfr[i]==0);
 }
 /* No reads through absent/mismatched/undersized queue storage. */
 a.shared.bytes=sizeof(*a.table)-1;memset(a.sfr,'Q',512);capture_shared_state(&a);assert(a.sfr[0]=='Q');
 a.shared.bytes=capacity;a.table=NULL;capture_shared_state(&a);assert(a.sfr[0]=='Q');
 a.table=a.shared.cpu;free(a.shared.cpu);a.shared.cpu=NULL;capture_shared_state(&a);assert(a.sfr[0]=='Q');
 puts("A5_DIAGNOSTIC_PASS");
}
