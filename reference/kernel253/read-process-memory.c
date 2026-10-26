#define _GNU_SOURCE
#include <stdio.h>
#include <stdint.h>
#include <inttypes.h>
#include <stdlib.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
int main(int argc,char**argv){
 if(argc!=4)return 1;
 char *end;errno=0;long pid=strtol(argv[1],&end,10);if(errno||*end||pid<2)return 2;
 uint64_t address=strtoull(argv[2],&end,16);if(errno||*end)return 3;
 unsigned long length=strtoul(argv[3],&end,10);if(errno||*end||!length||length>4096)return 4;
 char path[64];snprintf(path,sizeof(path),"/proc/%ld/mem",pid);int fd=open(path,O_RDONLY|O_CLOEXEC);if(fd<0){perror("open mem");return 5;}
 unsigned char buf[4096];ssize_t n=pread(fd,buf,length,(off_t)address);close(fd);if(n!=(ssize_t)length){perror("pread mem");return 6;}
 size_t p=0;while(p<length){ssize_t wrote=write(STDOUT_FILENO,buf+p,length-p);if(wrote<=0)return 7;p+=wrote;}return 0;
}
