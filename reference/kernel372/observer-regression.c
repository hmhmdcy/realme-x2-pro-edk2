#include <assert.h>
#include <elf.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef uint32_t u32;typedef uint8_t u8;
#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))
#define IS_ALIGNED(x,a) (!((x)&((a)-1)))
#define min_t(t,a,b) ((t)(a)<(t)(b)?(t)(a):(t)(b))
#define max(a,b) ((a)>(b)?(a):(b))
#define CAMSS_A5_FW_WINDOW (5U*1024U*1024U)
#define EXPORT_SYMBOL_GPL(x)
#define module_param_array(...)
struct firmware {const u8 *data;size_t size;};
struct camss_a5_fw_layout {u32 entry,span,segments;};
struct camss_a5 {
 void *dev;bool power_held;
 struct {void *cpu;u32 bytes,mapped;} firmware;
 void (*failure_snapshot)(struct camss_a5 *a5);
};
static unsigned barrier_calls;
static void dma_rmb(void) {++barrier_calls;}
static u32 get_unaligned_le32(const void *p) {const u8 *b=p;return (u32)b[0]|(u32)b[1]<<8|(u32)b[2]<<16|(u32)b[3]<<24;}
static unsigned get_unaligned_le16(const void *p) {const u8 *b=p;return b[0]|(unsigned)b[1]<<8;}
#define dev_info(dev,...) ((void)(dev),printf(__VA_ARGS__))
#include "fw-validation.inc"
#include "observer.inc"
int main(int argc,char **argv)
{
 assert(argc==3);int scenario=atoi(argv[1]);FILE *f=fopen(argv[2],"rb");assert(f);assert(!fseek(f,0,SEEK_END));long length=ftell(f);rewind(f);
 u8 *raw=malloc(length),*memory=calloc(1,CAMSS_A5_FW_WINDOW);assert(raw&&memory);assert(fread(raw,1,length,f)==(size_t)length);fclose(f);
 struct firmware fw={raw,length};struct camss_a5 a={.power_held=true,.firmware={memory,CAMSS_A5_FW_WINDOW,CAMSS_A5_FW_WINDOW}};
 snapshot_offset_count=snapshot_word_count=4;
 unsigned offsets[]={4096,5000,6000,8000},words_count[]={3,1,40,32};
 memcpy(snapshot_offsets,offsets,sizeof(offsets));memcpy(snapshot_words,words_count,sizeof(words_count));
 int expected=0;
 if(scenario==7){snapshot_offsets[0]=4097;expected=-EINVAL;}
 if(scenario==8){snapshot_offsets[0]=UINT32_MAX-3;expected=-EINVAL;}
 if(scenario==9){snapshot_words[0]=97;expected=-EINVAL;}
 if(scenario==10){snapshot_words[0]=0;expected=-EINVAL;}
 if(scenario==11){snapshot_word_count=3;expected=-EINVAL;}
 if(scenario==12){snapshot_offset_count=snapshot_word_count=0;}
 if(scenario==13){snapshot_offset_count=snapshot_word_count=5;expected=-EINVAL;}
 if(scenario==14){u32 table=get_unaligned_le32(raw+28);u32 n=4095;memcpy(raw+table+16,&n,4);expected=-ENOEXEC;}
 if(scenario==15){fw.size=47;expected=-ENOEXEC;}
 if(scenario==16){snapshot_offset_count=snapshot_word_count=1;snapshot_offsets[0]=0x384000-4;snapshot_words[0]=1;}
 if(scenario==17){snapshot_offsets[0]=0x384000-4;snapshot_words[0]=2;expected=-EINVAL;}
 if(scenario==18){snapshot_offset_count=0;expected=-EINVAL;}
 assert(configure_snapshot(&a,&fw)==expected);
 if(expected || scenario==12){assert(!a.failure_snapshot && !snapshot_boot_code);free(memory);free(raw);return 0;}
 assert(a.failure_snapshot && snapshot_boot_code);memcpy(memory,snapshot_boot_code,4096);
 for(unsigned i=0;i<snapshot_offset_count;i++)for(unsigned j=0;j<snapshot_words[i];j++){
  u32 value=0x55aa0000U+(i<<8)+j;memcpy(memory+snapshot_offsets[i]+j*4,&value,4);
 }
 if(scenario==1)memory[0]^=1;
 if(scenario==2)a.power_held=false;
 if(scenario==3)a.firmware.cpu=NULL;
 if(scenario==4)a.firmware.mapped--;
 if(scenario==5)snapshot_boot_code=NULL;
 if(scenario==6)a.firmware.bytes=4095;
 a.failure_snapshot(&a);
 assert(barrier_calls==(scenario==0||scenario==1||scenario==16));
 free(memory);free(raw);return 0;
}
