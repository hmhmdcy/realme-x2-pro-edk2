/* SPDX-License-Identifier: GPL-2.0-only */
/* Development-only readback: caller owns the live V4L2 stream throughout. */
static uint32_t mmio_read(volatile uint32_t *base, unsigned offset)
{
 uint32_t value=base[offset/4];__sync_synchronize();return value;
}
static void mmio_write(volatile uint32_t *base,unsigned offset,uint32_t value)
{
 __sync_synchronize();base[offset/4]=value;__sync_synchronize();
}
static int read_file(const char *path,unsigned char *data,size_t capacity)
{
 int fd=open(path,O_RDONLY|O_CLOEXEC);if(fd<0)return -1;
 ssize_t n=read(fd,data,capacity);int saved=errno;close(fd);errno=saved;
 return n<0?-1:(int)n;
}
static uint64_t be64(const unsigned char *p)
{
 uint64_t value=0;for(unsigned i=0;i<8;i++)value=(value<<8)|p[i];return value;
}
static int gamma_readback(void)
{
 glob_t nodes={0};int result=-1,fd=-1;void *mapping=MAP_FAILED;
 if(glob("/sys/bus/platform/drivers/qcom-camss/*/of_node/reg-names",0,NULL,&nodes)||nodes.gl_pathc!=1){errno=ENODEV;goto out;}
 char path[1024];unsigned char names[2048],registers[2048],status[32];
 if(snprintf(path,sizeof(path),"%s",nodes.gl_pathv[0])>=(int)sizeof(path)){errno=ENAMETOOLONG;goto out;}
 int count=read_file(path,names,sizeof(names));if(count<=0||names[count-1]){errno=EINVAL;goto out;}
 char *end=strstr(path,"/of_node/reg-names");if(!end){errno=EINVAL;goto out;}
 snprintf(end,(size_t)(path+sizeof(path)-end),"/power/runtime_status");
 int n=read_file(path,status,sizeof(status));if(n!=7||memcmp(status,"active\n",7)){errno=EHOSTDOWN;goto out;}
 snprintf(end,(size_t)(path+sizeof(path)-end),"/of_node/reg");
 int length=read_file(path,registers,sizeof(registers));if(length<=0){errno=EINVAL;goto out;}
 size_t index=0;uint64_t address=0,size=0;
 for(int pos=0;pos<count;){size_t len=strnlen((char *)names+pos,(size_t)(count-pos));
  if(len==(size_t)(count-pos)||16*(index+1)>(size_t)length){errno=EINVAL;goto out;}
  if(!strcmp((char *)names+pos,"vfe0")){address=be64(registers+16*index);size=be64(registers+16*index+8);}
  pos+=(int)len+1;index++;
 }
 if((size_t)length!=16*index||address<0xa000000||address>=0xb000000||address%4096||size<0xc34||size>0x20000){errno=ERANGE;goto out;}
 fd=open("/dev/mem",O_RDWR|O_SYNC|O_CLOEXEC);if(fd<0)goto out;
 mapping=mmap(NULL,size,PROT_READ|PROT_WRITE,MAP_SHARED,fd,(off_t)address);if(mapping==MAP_FAILED)goto out;
 volatile uint32_t *base=mapping;
 uint32_t saved_cfg=mmio_read(base,0xc24),saved_addr=mmio_read(base,0xc28),lut=mmio_read(base,0x798);
 uint32_t saved_cgc=mmio_read(base,0x34);
 mmio_write(base,0x34,saved_cgc|8u);
 printf("GAMMA_CGC before=%08x active=%08x\n",saved_cgc,mmio_read(base,0x34));
 printf("DMI_BEGIN cfg=%08x addr=%08x lut_cfg=%08x\n",saved_cfg,saved_addr,lut);
 /* No LUT writes. Read both physical banks, with explicit word indices. */
 for(unsigned auto_inc=0;auto_inc<2;auto_inc++)for(unsigned selector=26;selector<=31;selector++){
  uint32_t cfg=(saved_cfg&~0x1ffu)|(auto_inc<<8)|selector;
  mmio_write(base,0xc24,cfg);
  printf("DMI_TABLE auto_inc=%u selector=%u cfg=%08x words=",auto_inc,selector,mmio_read(base,0xc24));
  mmio_write(base,0xc28,0);
  for(unsigned i=0;i<64;i++){
   if(!auto_inc)mmio_write(base,0xc28,i);
   uint32_t value=mmio_read(base,0xc30);
   printf("%s%08x",i?",":"",value);
  }
  printf(" addr_after=%08x\n",mmio_read(base,0xc28));
 }
 mmio_write(base,0xc24,saved_cfg);mmio_write(base,0xc28,saved_addr);
 mmio_write(base,0x34,saved_cgc);
 result=(mmio_read(base,0xc24)==saved_cfg&&mmio_read(base,0xc28)==saved_addr&&mmio_read(base,0x34)==saved_cgc)?0:-1;
 printf("DMI_END state_restored=%d\n",!result);fflush(stdout);
 if(result)errno=EIO;
out:
 if(mapping!=MAP_FAILED)munmap(mapping,size);
 if(fd>=0)close(fd);globfree(&nodes);return result;
}
