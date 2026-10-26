/* SPDX-License-Identifier: MIT */
/* Independent fixed packed40 decoder for the original module's 221-point array. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void unpack(const unsigned char p[5], uint16_t out[4])
{
 out[0]=(uint16_t)p[0] | (uint16_t)(p[4]&0xc0)<<2;
 out[1]=(uint16_t)p[1] | (uint16_t)(p[4]&0x30)<<4;
 out[2]=(uint16_t)p[2] | (uint16_t)(p[4]&0x0c)<<6;
 out[3]=(uint16_t)p[3] | (uint16_t)(p[4]&0x03)<<8;
}
int main(int argc,char **argv)
{
 if(argc!=2)return 2;
 if(!strcmp(argv[1],"--self-test")){
  const unsigned char input[5]={0x12,0x34,0x56,0x78,0x9c};
  const uint16_t expected[4]={0x212,0x134,0x356,0x078};uint16_t out[4];
  unpack(input,out);if(memcmp(out,expected,sizeof(out)))return 3;
  const unsigned char high[5]={255,255,255,255,255};unpack(high,out);
  for(unsigned int c=0;c<4;c++)if(out[c]!=1023)return 4;
  const unsigned char zero[5]={0};unpack(zero,out);
  for(unsigned int c=0;c<4;c++)if(out[c])return 5;
  puts("LSC_PACKED40_SELF_TEST_PASS");return 0;
 }
 unsigned char raw[12287];FILE *f=fopen(argv[1],"rb");if(!f)return 6;
 if(fread(raw,1,sizeof(raw),f)!=sizeof(raw)||fgetc(f)!=EOF){fclose(f);return 7;}fclose(f);
 uint16_t result[4][221];
 for(unsigned int i=0;i<221;i++){
  uint16_t point[4];unpack(raw+208+i*5,point);
  for(unsigned int c=0;c<4;c++)result[c][i]=point[c];
 }
 return fwrite(result,1,sizeof(result),stdout)==sizeof(result)?0:8;
}
