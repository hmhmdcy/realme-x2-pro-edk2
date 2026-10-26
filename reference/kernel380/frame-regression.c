#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
typedef uint8_t u8;typedef uint16_t u16;typedef uint32_t u32;typedef uint64_t u64;
#define EXPORT_SYMBOL_GPL(x)
static u16 get_unaligned_le16(const void *p){u16 v;memcpy(&v,p,2);return v;}
static u32 get_unaligned_le32(const void *p){u32 v;memcpy(&v,p,4);return v;}
static void put_unaligned_le16(u16 v,void *p){memcpy(p,&v,2);}
static void put_unaligned_le32(u32 v,void *p){memcpy(p,&v,4);}
static void put_unaligned_le64(u64 v,void *p){memcpy(p,&v,8);}
#include "actual-header.h"
#include "actual-body.inc"
int main(int argc,char **argv){
 assert(argc==8);unsigned width=strtoul(argv[1],0,0),height=strtoul(argv[2],0,0),port=strtoul(argv[3],0,0),cores=strtoul(argv[4],0,0),bl=strtoul(argv[6],0,0);bool negative=!strcmp(argv[7],"negative");
 FILE *in=fopen(argv[5],"rb");assert(in);assert(!fseek(in,0,SEEK_END));long size=ftell(in);assert(size>=2268 && size<65536);rewind(in);u8 *stripe=malloc(size);assert(stripe && fread(stripe,1,size,in)==(size_t)size);fclose(in);
 struct camss_a5_ipe_io io={.input={width,height,width,height,false},.output={width,height,width,height,false},.output_port=port};
 struct camss_a5_ipe_frame frame={.striping={0x6004000,size},.iq={0x6009000,2584},.scratch={0x20000000,48},.bl={0x23000000,bl},.input={0x21000000,width*height*3/2},.output={0x24000000,width*height*3/2},.striping_cpu=stripe,.required_scratch_bytes=48,.required_bl_bytes=bl,.request_id=1,.max_cores=cores,.target_time_ns=1000000,.user_data=0x13579bdf2468ace0ULL};
 u8 out[3816];assert(!camss_a5_ipe_encode_frame(out,sizeof(out),&io,&frame));
 if(!negative){assert(fwrite(out,1,sizeof(out),stdout)==sizeof(out));free(stripe);return 0;}
 unsigned cases=0;
 for(unsigned bad=0;bad<38;bad++){
  struct camss_a5_ipe_io testio=io;struct camss_a5_ipe_frame test=frame;u8 saved[3816];memset(out,0xa5,sizeof(out));memcpy(saved,out,sizeof(out));
  u32 pass=get_unaligned_le32(stripe+20);u16 count=get_unaligned_le16(stripe+428);
  if(bad==4)testio.output_port=0;if(bad==5)test.max_cores=0;if(bad==6)test.max_cores=3;if(bad==7)test.target_time_ns=0;
  if(bad==8)test.required_scratch_bytes=0;if(bad==9)test.required_bl_bytes=0;if(bad==10)test.scratch.bytes=47;if(bad==11)test.bl.bytes=bl-1;if(bad==12)test.iq.bytes=2583;
  if(bad==13)test.striping.bytes=2267;if(bad==14)put_unaligned_le32(0,stripe+20);if(bad==15)put_unaligned_le32(5,stripe+20);if(bad==16)put_unaligned_le16(0,stripe+428);if(bad==17)put_unaligned_le16(65535,stripe+428);
  if(bad==18)test.input.iova=0;if(bad==19)test.output.iova++;if(bad==20){test.output.iova=0xfffff000;test.output.bytes=8192;}
  if(bad==21)testio.input.width--;if(bad==22)testio.output.height--;if(bad==23)testio.input.stride-=2;if(bad==24)testio.output.slice_height-=2;
  if(bad==25)test.input.bytes--;if(bad==26)test.output.bytes--;if(bad==27){testio.input.stride=0xfffffffe;testio.input.slice_height=0xfffffffe;}
  if(bad==28)test.striping_cpu=NULL;if(bad==29)testio.input.width=0;if(bad==30)testio.output.height=0;if(bad==31)test.bl.bytes=31;
  if(bad>=32){struct camss_a5_ipe_buffer *buffers[]={&test.striping,&test.iq,&test.scratch,&test.bl,&test.input,&test.output};buffers[bad-32]->bytes=0;}
  assert(camss_a5_ipe_encode_frame(bad==0?NULL:out,bad==1?3815:sizeof(out),bad==2?NULL:&testio,bad==3?NULL:&test)==-EINVAL && !memcmp(out,saved,sizeof(out)));
  put_unaligned_le32(pass,stripe+20);put_unaligned_le16(count,stripe+428);cases++;
 }
 for(unsigned i=0;i<6;i++)for(unsigned j=i+1;j<6;j++){
  struct camss_a5_ipe_frame test=frame;struct camss_a5_ipe_buffer *buffers[]={&test.striping,&test.iq,&test.scratch,&test.bl,&test.input,&test.output};buffers[i]->iova=buffers[j]->iova;memset(out,0xa5,sizeof(out));
  assert(camss_a5_ipe_encode_frame(out,sizeof(out),&io,&test)==-EINVAL);for(unsigned n=0;n<sizeof(out);n++)assert(out[n]==0xa5);cases++;
 }
 u32 used=0x12345678;assert(camss_a5_ipe_striping_bytes(NULL,size,&used)==-EINVAL && used==0x12345678);cases++;
 assert(camss_a5_ipe_striping_bytes(stripe,size,NULL)==-EINVAL);cases++;
 printf("FRAME_INVALID_CASES %u\n",cases);free(stripe);return 0;
}
