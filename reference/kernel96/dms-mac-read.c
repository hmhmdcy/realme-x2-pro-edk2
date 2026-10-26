/* Bounded, read-only DMS Get MAC Address (0x005c) over QRTR.
 * No generic QMI command input, modem mode changes, NV writes, or reset.
 * Successful identities stay in fixed private RAM files, not stdout.
 * Protocol: libqmi data/qmi-service-dms.json and qmi-enums-dms.h. */
#define _GNU_SOURCE
#include <libqrtr.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

static uint16_t u16(const unsigned char *p) { return p[0]|((uint16_t)p[1]<<8); }
static int receive(int fd,unsigned char *buf,size_t size,struct sockaddr_qrtr *src)
{
    socklen_t len=sizeof(*src);
    int n=recvfrom(fd,buf,size,0,(struct sockaddr *)src,&len);
    if(n<0 || len!=sizeof(*src) || src->sq_family!=AF_QIPCRTR) return -1;
    return n;
}
int main(int argc,char **argv)
{
    if(argc!=2 || (strcmp(argv[1],"wlan") && strcmp(argv[1],"bt"))) return 2;
    unsigned kind=!strcmp(argv[1],"bt");
    const char *path=kind?"/tmp/k96-verified-bt-mac-le.bin":"/tmp/k96-verified-wlan-mac-le.bin";
    if(!access(path,F_OK)) {fputs("Private output already exists\n",stderr);return 2;}
    umask(077);
    alarm(25);
    int fd=qrtr_open(0);if(fd<0) {perror("qrtr_open");return 3;}
    if(qrtr_new_lookup(fd,2,1,0)<0) {perror("DMS lookup");close(fd);return 3;}
    unsigned char buf[4096];struct sockaddr_qrtr src;
    uint32_t node=0,port=0;unsigned matches=0;
    time_t end=time(NULL)+5;
    while(time(NULL)<end && qrtr_poll(fd,1000)>0) {
        int n=receive(fd,buf,sizeof(buf),&src);struct qrtr_packet packet={0};
        if(n<0 || qrtr_decode(&packet,buf,n,&src)) {close(fd);return 3;}
        if(packet.type==QRTR_TYPE_NEW_SERVER && packet.service==2 && packet.version==1 && packet.instance==0 && packet.port) {
            node=packet.node;port=packet.port;matches++;
        }
        if(packet.type==QRTR_TYPE_NEW_SERVER && !packet.service && !packet.port) break;
    }
    if(matches!=1) {fprintf(stderr,"DMS service matches=%u\n",matches);close(fd);return 3;}
    printf("DMS endpoint node=%u port=%u operation=GET_MAC kind=%s\n",node,port,argv[1]);
    /* 7-byte QMI service header + mandatory uint32 Device TLV. */
    unsigned char request[14]={0,1,0,0x5c,0,7,0,1,4,0,0,0,0,0};request[10]=kind;
    /* libqrtr normalizes a successful send to 0, unlike sendto(2). */
    if(qrtr_sendto(fd,node,port,request,sizeof(request))<0) {perror("GET_MAC send");close(fd);return 3;}
    end=time(NULL)+10;
    while(time(NULL)<end) {
        if(qrtr_poll(fd,1000)<=0) continue;
        int n=receive(fd,buf,sizeof(buf),&src);if(n<0) {close(fd);return 3;}
        if(src.sq_node!=node || src.sq_port!=port) continue;
        if(n<7 || buf[0]!=QMI_RESPONSE || u16(buf+1)!=1 || u16(buf+3)!=0x5c || u16(buf+5)!=n-7) {close(fd);return 4;}
        const char *response_path=kind?"/tmp/k96-verified-bt-dms-response.bin":"/tmp/k96-verified-wlan-dms-response.bin";
        int response_file=open(response_path,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0600);
        if(response_file<0 || write(response_file,buf,n)!=n) {if(response_file>=0)close(response_file);close(fd);return 7;}
        close(response_file);
        unsigned result_seen=0,mac_seen=0;uint16_t result=0,error=0;unsigned char mac[6];
        for(size_t off=7;off<(size_t)n;) {
            if(off+3>(size_t)n) {close(fd);return 4;}
            unsigned type=buf[off];size_t len=u16(buf+off+1);off+=3;
            if(len>(size_t)n-off) {close(fd);return 4;}
            if(type==2) {
                if(result_seen++ || len!=4) {close(fd);return 4;}
                result=u16(buf+off);error=u16(buf+off+2);
            } else if(type==0x10) {
                if(mac_seen++ || len!=7 || buf[off]!=6) {close(fd);return 4;}
                memcpy(mac,buf+off+1,6);
            }
            off+=len;
        }
        printf("QMI result=%u error=%u mac_tlv_count=%u\n",result,error,mac_seen);
        if(result_seen!=1 || result || error || mac_seen!=1) {close(fd);return 5;}
        unsigned nonzero=0,notff=0;for(unsigned i=0;i<6;i++){nonzero|=mac[i];notff|=mac[i]^255;}
        /* Same-handset cnss-daemon validates the final octet's low two bits,
         * then reverses the six-byte DMS array for the WLAN MAC. The installed
         * BT HAL's DMS address function copies all six bytes unchanged. Retain
         * this verified little-endian representation; MGMT uses it directly.
         * Require a globally administered unicast provisioned identity. */
        if(!nonzero || !notff || (mac[5]&3)) {fputs("Rejected invalid provisioned address\n",stderr);close(fd);return 6;}
        int output=open(path,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0600);
        if(output<0 || write(output,mac,6)!=6 || fsync(output)) {perror("Private address output");if(output>=0)close(output);close(fd);return 7;}
        close(output);close(fd);puts("READ_ONLY_MAC_RESPONSE_SAVED");return 0;
    }
    close(fd);fputs("DMS response timeout\n",stderr);return 8;
}
