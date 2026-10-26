/* SPDX-License-Identifier: MIT */
/* Target-specific data framing: 51 packed40 points followed by one byte. */
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static void decode(const unsigned char *cursor,uint16_t result[4][221])
{
 unsigned in_group=0;
 for(unsigned point=0;point<221;point++){
  uint64_t word=0;
  for(unsigned byte=0;byte<5;byte++)word|=(uint64_t)*cursor++<<(byte*8);
  for(unsigned c=0;c<4;c++)result[c][point]=((word>>(8*c))&255)|(((word>>(38-2*c))&3)<<8);
  if(++in_group==51){cursor++;in_group=0;}
 }
}

int main(int argc,char **argv)
{
 if(argc!=2)return 2;
 uint16_t result[4][221];
 if(!strcmp(argv[1],"--self-test")){
  unsigned char encoded[1109],*cursor=encoded;unsigned in_group=0;
  for(unsigned i=0;i<221;i++){
   unsigned high=0;
   for(unsigned c=0;c<4;c++){unsigned v=(i*37+c*173+11)%1024;*cursor++=v;high|=(v>>8)<<(6-2*c);}
   *cursor++=high;
   if(++in_group==51){*cursor++=0xa5;in_group=0;}
  }
  if(cursor-encoded!=1109)return 3;
  decode(encoded,result);
  for(unsigned i=0;i<221;i++)for(unsigned c=0;c<4;c++)if(result[c][i]!=(i*37+c*173+11)%1024)return 4;
  puts("STOCK_LSC framing and asymmetric packed40 vectors passed");return 0;
 }
 unsigned char data[12287];FILE *file=fopen(argv[1],"rb");if(!file)return 5;
 if(fread(data,1,sizeof(data),file)!=sizeof(data)||fgetc(file)!=EOF){fclose(file);return 6;}
 fclose(file);decode(data+208,result);
 return fwrite(result,1,sizeof(result),stdout)==sizeof(result)?0:7;
}
