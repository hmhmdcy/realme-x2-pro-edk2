/* SPDX-License-Identifier: GPL-2.0-only */
/* Bounded synthetic-stream experiment; no device calibration or persistent writes. */
static uint32_t gamma_saved_lut, gamma_saved_cgc, gamma_saved_dmi, gamma_saved_addr;
static uint32_t gamma_old_words[3][64];
static volatile uint32_t *gamma_base;
static size_t gamma_mapping_size;
static int gamma_mapping_fd=-1;
static unsigned gamma_restore_selectors[3];
static int gamma_probe_upload(void)
{
 static const uint16_t points[65]={
  0,135,199,246,284,317,347,373,398,421,442,462,481,500,517,534,
  550,565,580,595,609,623,636,649,662,674,686,698,709,720,732,742,
  753,763,774,784,794,803,813,823,832,841,850,859,868,877,885,894,
  902,910,918,926,934,942,950,958,966,973,981,988,995,1003,1010,1017,1024
 };
 static const unsigned selectors[3]={30,26,28};
 glob_t nodes={0};char path[1024];unsigned char names[2048],registers[2048],status[32];
 if(glob("/sys/bus/platform/drivers/qcom-camss/*/of_node/reg-names",0,NULL,&nodes)||nodes.gl_pathc!=1){globfree(&nodes);errno=ENODEV;return -1;}
 if(snprintf(path,sizeof(path),"%s",nodes.gl_pathv[0])>=(int)sizeof(path)){globfree(&nodes);errno=EINVAL;return -1;}globfree(&nodes);
 int count=read_file(path,names,sizeof(names));if(count<=0||names[count-1]){errno=EINVAL;return -1;}
 char *end=strstr(path,"/of_node/reg-names");if(!end){errno=EINVAL;return -1;}
 snprintf(end,(size_t)(path+sizeof(path)-end),"/power/runtime_status");
 if(read_file(path,status,sizeof(status))!=7||memcmp(status,"active\n",7)){errno=EHOSTDOWN;return -1;}
 snprintf(end,(size_t)(path+sizeof(path)-end),"/of_node/reg");int length=read_file(path,registers,sizeof(registers));
 size_t index=0;uint64_t address=0,size=0;
 for(int pos=0;pos<count;){size_t len=strnlen((char *)names+pos,(size_t)(count-pos));
  if(len==(size_t)(count-pos)||16*(index+1)>(size_t)length){errno=EINVAL;return -1;}
  if(!strcmp((char *)names+pos,"vfe0")){address=be64(registers+16*index);size=be64(registers+16*index+8);}pos+=(int)len+1;index++;
 }
 if((size_t)length!=16*index||address<0xa000000||address>=0xb000000||address%4096||size<0xc34||size>0x20000){errno=ERANGE;return -1;}
 gamma_mapping_fd=open("/dev/mem",O_RDWR|O_SYNC|O_CLOEXEC);if(gamma_mapping_fd<0)return -1;
 void *mapping=mmap(NULL,size,PROT_READ|PROT_WRITE,MAP_SHARED,gamma_mapping_fd,(off_t)address);
 if(mapping==MAP_FAILED){close(gamma_mapping_fd);gamma_mapping_fd=-1;return -1;}
 gamma_base=mapping;gamma_mapping_size=size;
 gamma_saved_lut=mmio_read(gamma_base,0x798);gamma_saved_cgc=mmio_read(gamma_base,0x34);
 gamma_saved_dmi=mmio_read(gamma_base,0xc24);gamma_saved_addr=mmio_read(gamma_base,0xc28);
 mmio_write(gamma_base,0x34,gamma_saved_cgc|8u);
 unsigned verified=0;
 for(unsigned ch=0;ch<3;ch++){
  unsigned bank=!(gamma_saved_lut&(1u<<ch));unsigned select=selectors[ch]+bank;gamma_restore_selectors[ch]=select;
  mmio_write(gamma_base,0xc24,(gamma_saved_dmi&~0xffu)|select);
  for(unsigned i=0;i<64;i++){mmio_write(gamma_base,0xc28,i);gamma_old_words[ch][i]=mmio_read(gamma_base,0xc30);}
  for(unsigned i=0;i<64;i++){uint32_t packed=points[i]|((uint32_t)(points[i+1]-points[i])<<10);mmio_write(gamma_base,0xc28,i);mmio_write(gamma_base,0xc30,packed);}
  unsigned matches=0;
  for(unsigned i=0;i<64;i++){uint32_t packed=points[i]|((uint32_t)(points[i+1]-points[i])<<10);mmio_write(gamma_base,0xc28,i);matches+=mmio_read(gamma_base,0xc30)==packed;}
  verified+=matches;printf("GAMMA_UPLOAD channel=%u selector=%u matching_words=%u expected=64\n",ch,select,matches);
 }
 mmio_write(gamma_base,0xc24,gamma_saved_dmi);mmio_write(gamma_base,0xc28,gamma_saved_addr);
 mmio_write(gamma_base,0x34,gamma_saved_cgc);
 if(verified!=192){errno=EIO;return -1;}
 mmio_write(gamma_base,0x798,gamma_saved_lut^7u);mmio_write(gamma_base,0x4ac,1u);
 printf("GAMMA_SWITCH before=%08x active=%08x readback_words=%u\n",gamma_saved_lut,mmio_read(gamma_base,0x798),verified);fflush(stdout);return 0;
}
static void gamma_probe_restore(void)
{
 if(!gamma_base)return;
 mmio_write(gamma_base,0x798,gamma_saved_lut);mmio_write(gamma_base,0x4ac,1u);
 /* Keep the newly inactive bank unselected for a complete 320x240 TPG frame. */
 usleep(20000);
 mmio_write(gamma_base,0x34,gamma_saved_cgc|8u);
 for(unsigned ch=0;ch<3;ch++){
  if(gamma_restore_selectors[ch]<26||gamma_restore_selectors[ch]>31)continue;
  mmio_write(gamma_base,0xc24,(gamma_saved_dmi&~0xffu)|gamma_restore_selectors[ch]);
  for(unsigned i=0;i<64;i++){mmio_write(gamma_base,0xc28,i);mmio_write(gamma_base,0xc30,gamma_old_words[ch][i]);}
 }
 mmio_write(gamma_base,0xc24,gamma_saved_dmi);mmio_write(gamma_base,0xc28,gamma_saved_addr);mmio_write(gamma_base,0x34,gamma_saved_cgc);
 printf("GAMMA_RESTORE registers=%d\n",mmio_read(gamma_base,0x798)==gamma_saved_lut&&mmio_read(gamma_base,0x34)==gamma_saved_cgc&&mmio_read(gamma_base,0xc24)==gamma_saved_dmi&&mmio_read(gamma_base,0xc28)==gamma_saved_addr);
 munmap((void *)gamma_base,gamma_mapping_size);close(gamma_mapping_fd);gamma_base=NULL;
}
