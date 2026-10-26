/* Bounded Bluetooth MGMT observations; all identities are private output. */
#define _GNU_SOURCE
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <poll.h>
#include <endian.h>
#include <time.h>
struct addr_hci { sa_family_t family; uint16_t dev, channel; };
static int fd;
static uint16_t u16(const unsigned char *p) { return p[0] | (p[1]<<8); }
static void fail(const char *s) { perror(s); exit(1); }
static void send_cmd(uint16_t op, uint16_t idx, const void *payload, uint16_t len)
{
    uint16_t hdr[3]={htole16(op),htole16(idx),htole16(len)};
    unsigned char buf[512];
    if (len>sizeof(buf)-sizeof(hdr)) exit(2);
    memcpy(buf,hdr,6); if(len) memcpy(buf+6,payload,len);
    ssize_t sent=send(fd,buf,6+len,0);
    if(sent<0) fail("send");
    if(sent!=0 && sent!=6+len) {fprintf(stderr,"short MGMT send: %zd\n",sent);exit(2);}
}
static int receive(unsigned char *buf, int timeout)
{
    struct pollfd p={fd,POLLIN,0}; int n=poll(&p,1,timeout);
    if(n<0) fail("poll"); if(!n) return 0;
    n=recv(fd,buf,4096,0); if(n<0) fail("recv");
    if(n<6 || u16(buf+4)!=n-6) exit(2);
    return n;
}
static void event(const unsigned char *b, int n)
{
    printf("event=0x%04x index=%u len=%u",u16(b),u16(b+2),u16(b+4));
    if(u16(b)==0x12 && n>=20) {
        const unsigned char *p=b+6;
        printf(" address=%02X:%02X:%02X:%02X:%02X:%02X type=%u rssi=%d",p[5],p[4],p[3],p[2],p[1],p[0],p[6],(int8_t)p[7]);
        unsigned len=u16(p+12); if(len>(unsigned)n-20) exit(2);
        for(unsigned i=0;i<len;) {unsigned k=p[14+i]; if(!k || i+1+k>len) break;
            if((p[15+i]==8 || p[15+i]==9) && k>1) {printf(" name="); for(unsigned j=0;j<k-1;j++){unsigned char c=p[16+i+j]; putchar(c>=32?c:'.');}}
            i+=k+1;
        }
    }
    if(u16(b)==0x13 && n==8) printf(" type=%u discovering=%u",b[6],b[7]);
    printf("\n"); fflush(stdout);
}
static int command(uint16_t op,uint16_t idx,const void *data,uint16_t len)
{
    unsigned char b[4096]; send_cmd(op,idx,data,len);
    time_t end=time(NULL)+25;
    while(time(NULL)<end) {
        int n=receive(b,1000); if(!n) continue;
        if((u16(b)==1 || u16(b)==2) && n>=9 && u16(b+6)==op && u16(b+2)==idx) {
            printf("command=0x%04x status=0x%02x payload=",op,b[8]);
            for(int i=9;i<n;i++) printf("%02x",b[i]); puts("");
            return b[8]?1:0;
        }
        event(b,n);
    }
    fprintf(stderr,"MGMT command timed out\n"); return 1;
}
int main(int argc,char **argv)
{
    if(argc!=2 && !(argc==3 && (!strcmp(argv[1],"test-address") || !strcmp(argv[1],"dms-address")))) {fprintf(stderr,"Use info, setup, power, off, configure, scan-policy, scan, or test-address/dms-address PRIVATE_FILE\n");return 2;}
    fd=socket(31,SOCK_RAW|SOCK_CLOEXEC,1); if(fd<0) fail("socket");
    if(!strcmp(argv[1],"setup")) {int r=ioctl(fd,_IOW('H',201,int),0); if(r) perror("HCIDEVUP"); close(fd);return r?1:0;}
    struct addr_hci a={31,0xffff,3}; if(bind(fd,(void*)&a,sizeof(a))) fail("bind");
    int rc=0;
    if(!strcmp(argv[1],"info")) {rc|=command(3,0xffff,NULL,0);rc|=command(0x36,0xffff,NULL,0);rc|=command(4,0,NULL,0);}
    else if(!strcmp(argv[1],"power")) {unsigned char v=1;rc=command(5,0,&v,1);}
    else if(!strcmp(argv[1],"off")) {unsigned char v=0;rc=command(5,0,&v,1);}
    else if(!strcmp(argv[1],"test-address") || !strcmp(argv[1],"dms-address")) {
        unsigned char address[6];FILE *f=fopen(argv[2],"rb");if(!f)fail("address file");
        size_t n=fread(address,1,6,f);int extra=fgetc(f);fclose(f);
        /* DMS bytes are little-endian on this handset (installed HAL verified).
         * The caller must validate the read-only DMS response's provenance.
         * SET_PUBLIC_ADDRESS changes the controller's runtime identity only. */
        if(n!=6 || extra!=EOF)return 2;
        unsigned zero=0,notff=0;for(unsigned i=0;i<6;i++){zero|=address[i];notff|=address[i]^255;}
        if(!zero || !notff)return 2;
        unsigned flags=!strcmp(argv[1],"dms-address")?0:2;
        if((address[5]&3)!=flags)return 2;
        rc=command(0x39,0,address,6);
    }
    else if(!strcmp(argv[1],"configure")) {
        unsigned char off=0,on=1;
        rc=command(5,0,&off,1);
        if(!rc)rc=command(0xd,0,&on,1);
        if(!rc)rc=command(0xb,0,&on,1);
        if(!rc)rc=command(9,0,&off,1);
        if(!rc)rc=command(7,0,&off,1);
        if(!rc)rc=command(5,0,&on,1);
    }
    else if(!strcmp(argv[1],"scan-policy")) {
        /* Inquiry/LE discovery needs neither incoming connections nor bonding. */
        unsigned char off=0;
        rc=command(9,0,&off,1);
        if(!rc)rc=command(7,0,&off,1);
    }
    else if(!strcmp(argv[1],"scan")) {
        unsigned char type=7; rc=command(0x23,0,&type,1);
        if(!rc) {unsigned char b[4096];time_t end=time(NULL)+30;int ended=0;
            while(time(NULL)<end) {int n=receive(b,1000);if(n){event(b,n);if(u16(b)==0x13 && n==8 && !b[7]){ended=1;break;}}}
            if(!ended) rc=command(0x24,0,&type,1);
        }
    } else rc=2;
    close(fd); return rc;
}
