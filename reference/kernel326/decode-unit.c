/* SPDX-License-Identifier: MIT */
/* Sequential packed40 decoder, including actual descriptor byte aliases. */
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

static int number(const char *s, unsigned *out)
{
 char *end;errno=0;unsigned long n=strtoul(s,&end,0);
 if(errno || !*s || *end || n>65535)return -1;
 *out=(unsigned)n;return 0;
}
int main(int argc,char **argv)
{
 unsigned base,low[4];
 if(argc!=7 || number(argv[2],&base))return 2;
 for(unsigned c=0;c<4;c++)if(number(argv[c+3],&low[c]) || low[c]>3)return 2;
 FILE *file=fopen(argv[1],"rb");if(!file)return 3;
 if(fseek(file,(long)base,SEEK_SET)){fclose(file);return 4;}
 uint16_t result[4][221];unsigned group=0;
 for(unsigned i=0;i<221;i++){
  unsigned char point[5];
  if(fread(point,1,5,file)!=5){fclose(file);return 5;}
  for(unsigned c=0;c<4;c++)result[c][i]=(uint16_t)(point[low[c]]|(((point[4]>>(6-2*c))&3)<<8));
  if(++group==51){if(fgetc(file)==EOF){fclose(file);return 6;}group=0;}
 }
 fclose(file);
 for(unsigned c=0;c<4;c++)for(unsigned i=0;i<221;i++){
  unsigned char bytes[2]={(unsigned char)result[c][i],(unsigned char)(result[c][i]>>8)};
  if(fwrite(bytes,1,2,stdout)!=2)return 7;
 }
 return 0;
}
