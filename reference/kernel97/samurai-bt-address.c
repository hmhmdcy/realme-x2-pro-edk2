/* Provision a verified same-handset DMS address through runtime MGMT only.
 * No power-on, discovery, pairing, connection, raw HCI or NV operations.
 * All messages omit local/remote identities. Protocol: BlueZ mgmt-protocol.rst.
 */
#define _GNU_SOURCE
#include <sys/socket.h>
#include <sys/stat.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <poll.h>
#include <fcntl.h>
#include <endian.h>
#include <time.h>

struct addr_hci { sa_family_t family; uint16_t dev, channel; };
static int fd;
enum { INFO_SIZE=6+1+2+4+4+3+249+11 };
static uint16_t u16(const unsigned char *p) { return p[0]|((uint16_t)p[1]<<8); }
static uint32_t u32(const unsigned char *p) { return u16(p)|((uint32_t)u16(p+2)<<16); }
static long now_ms(void)
{
    struct timespec t;
    if(clock_gettime(CLOCK_MONOTONIC,&t)) exit(1);
    return t.tv_sec*1000+t.tv_nsec/1000000;
}
static int command(uint16_t op,uint16_t index,const void *data,uint16_t len,
                   unsigned char *reply,size_t capacity,size_t *length)
{
    unsigned char buf[4096];
    uint16_t hdr[3]={htole16(op),htole16(index),htole16(len)};
    if(len>sizeof(buf)-6) return 1;
    memcpy(buf,hdr,6);
    if(len) memcpy(buf+6,data,len);
    if(send(fd,buf,len+6,0)!=len+6) return 1;
    long deadline=now_ms()+15000;
    while(now_ms()<deadline) {
        struct pollfd p={fd,POLLIN,0};
        int result=poll(&p,1,500);
        if(result<0 || (p.revents&(POLLERR|POLLHUP|POLLNVAL))) return 1;
        if(!result) continue;
        int n=recv(fd,buf,sizeof(buf),0);
        if(n<6 || u16(buf+4)!=n-6) return 1;
        uint16_t event=u16(buf);
        if(u16(buf+2)!=index || (event!=1 && event!=2)) continue;
        if(n<9) return 1;
        /* Command Status has status before opcode; Command Complete has
         * opcode before status. Treat status failures without logging data. */
        if(event==2) {
            if(n!=9 || u16(buf+7)!=op) continue;
            fprintf(stderr,"MGMT status op=0x%04x status=%u\n",op,buf[6]);
            return 1;
        }
        if(u16(buf+6)!=op) continue;
        if(buf[8]) {
            fprintf(stderr,"MGMT failed op=0x%04x status=%u\n",op,buf[8]);
            return 1;
        }
        *length=n-9;
        if(*length>capacity) return 1;
        memcpy(reply,buf+9,*length);
        return 0;
    }
    fprintf(stderr,"MGMT timeout op=0x%04x\n",op);
    return 1;
}
static int indexes(uint16_t op,uint16_t *index)
{
    unsigned char reply[512]; size_t length;
    if(command(op,0xffff,NULL,0,reply,sizeof(reply),&length) || length<2) return -1;
    unsigned count=u16(reply);
    if(length!=2+count*2 || count>1) return -1;
    if(count) *index=u16(reply+2);
    return count;
}
static int verify(uint16_t index,const unsigned char address[6])
{
    unsigned char reply[512]; size_t length;
    if(command(4,index,NULL,0,reply,sizeof(reply),&length)) return 1;
    if(length!=INFO_SIZE) {fprintf(stderr,"Unexpected READ_INFO length=%zu\n",length);return 1;}
    if(memcmp(reply,address,6)) {fputs("Controller identity mismatch\n",stderr);return 1;}
    unsigned settings=u32(reply+13);
    if(settings&(2|8|16)) {
        if(settings&1) {fputs("Active controller accepts connections or bonding\n",stderr);return 1;}
        unsigned char off[3]={0};
        if((settings&16) && command(9,index,off,1,reply,sizeof(reply),&length)) return 1;
        if((settings&2) && command(7,index,off,1,reply,sizeof(reply),&length)) return 1;
        if((settings&8) && command(6,index,off,3,reply,sizeof(reply),&length)) return 1;
        if(command(4,index,NULL,0,reply,sizeof(reply),&length) || length!=INFO_SIZE || memcmp(reply,address,6)) return 1;
        settings=u32(reply+13);
        if(settings&(2|8|16)) return 1;
    }
    printf("BT_ADDRESS_VERIFIED index=%u powered=%u connectable=0 bondable=0\n",index,settings&1);
    return 0;
}
int main(int argc,char **argv)
{
    if(argc!=2 || geteuid()) return 2;
    alarm(60);
    int file=open(argv[1],O_RDONLY|O_NOFOLLOW|O_CLOEXEC);
    struct stat attrs; unsigned char address[6];
    if(file<0 || fstat(file,&attrs) || !S_ISREG(attrs.st_mode) || attrs.st_uid ||
       (attrs.st_mode&0777)!=0600 || attrs.st_size!=6 || read(file,address,6)!=6) return 2;
    close(file);
    unsigned nonzero=0,notff=0;
    for(unsigned i=0;i<6;i++){nonzero|=address[i];notff|=address[i]^255;}
    if(!nonzero || !notff || (address[5]&3)) return 2;
    fd=socket(31,SOCK_RAW|SOCK_CLOEXEC,1);
    if(fd<0) return 1;
    struct addr_hci a={31,0xffff,3};
    if(bind(fd,(void *)&a,sizeof(a))) return 1;
    uint16_t index=0xffff,unconfigured=0xffff;
    int configured=0,pending=0;
    long initialization=now_ms()+20000;
    while(now_ms()<initialization) {
        configured=indexes(3,&index); pending=indexes(0x36,&unconfigured);
        if(configured<0 || pending<0 || configured+pending>1) return 1;
        if(configured+pending==1) break;
        usleep(200000);
    }
    if(configured+pending!=1) {fputs("Controller initialization timeout\n",stderr);return 1;}
    if(configured==1) return verify(index,address);
    unsigned char reply[512]; size_t length;
    if(command(0x37,unconfigured,NULL,0,reply,sizeof(reply),&length) || length!=10 ||
       !(u32(reply+2)&2) || u32(reply+6)!=2) return 1;
    if(command(0x39,unconfigured,address,6,reply,sizeof(reply),&length) || length!=4 || u32(reply)) return 1;
    long deadline=now_ms()+20000;
    while(now_ms()<deadline) {
        configured=indexes(3,&index);
        if(configured<0) return 1;
        if(configured==1) {
            int result=verify(index,address);
            close(fd);
            return result;
        }
        usleep(200000);
    }
    fputs("Configured controller did not appear\n",stderr);
    close(fd);
    return 1;
}
