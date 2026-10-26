/* SPDX-License-Identifier: MIT */
#define _GNU_SOURCE
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/if_ether.h>
#include <linux/if_packet.h>
#include <net/if.h>
#include <poll.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <time.h>
#include <unistd.h>

static double monotime(void)
{
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) { perror("clock"); exit(1); }
    return t.tv_sec + t.tv_nsec / 1e9;
}

int main(int argc, char **argv)
{
    unsigned char packet[65536];
    struct in_addr targets[8];
    struct sockaddr_ll bindaddr = { .sll_family=AF_PACKET, .sll_protocol=htons(ETH_P_IP) };
    struct tpacket_stats stats = {0};
    socklen_t statlen=sizeof(stats);
    uint32_t header[]={0xa1b2c3d4,0x00040002,0,0,65536,101};
    unsigned long packets=0,bytes=0;
    int fd,file,seconds,failed=0,limit=0;
    FILE *output;
    if (argc<5 || argc>12 || strcmp(argv[1],"wlan0")) {
        fprintf(stderr,"usage: capture wlan0 SECONDS PCAP TEST_SERVER_IPV4...\n"); return 2;
    }
    char *end;
    seconds=(int)strtol(argv[2],&end,10);
    if (*end || seconds<1 || seconds>60) return 2;
    for (int i=4;i<argc;i++) if (inet_pton(AF_INET,argv[i],&targets[i-4])!=1) return 2;
    bindaddr.sll_ifindex=(int)if_nametoindex(argv[1]);
    if (!bindaddr.sll_ifindex) { perror("ifindex"); return 1; }
    fd=socket(AF_PACKET,SOCK_DGRAM|SOCK_CLOEXEC,htons(ETH_P_IP));
    if (fd<0) { perror("packet socket"); return 1; }
    if (bind(fd,(void *)&bindaddr,sizeof(bindaddr))) { perror("bind"); close(fd); return 1; }
    file=open(argv[3],O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0600);
    if (file<0) { perror("new private capture"); close(fd); return 1; }
    output=fdopen(file,"wb");
    if (!output) { perror("fdopen"); close(file); close(fd); return 1; }
    if (fwrite(header,sizeof(header),1,output)!=1) { perror("header"); fclose(output); close(fd); return 1; }
    puts("CAPTURE_READY");fflush(stdout);
    double deadline=monotime()+seconds;
    while (monotime()<deadline) {
        struct pollfd p={.fd=fd,.events=POLLIN};
        int ret=poll(&p,1,100);
        if (ret<0) { if (errno==EINTR) continue; perror("poll");failed=1;break; }
        if (!ret) continue;
        ssize_t n=recv(fd,packet,sizeof(packet),MSG_DONTWAIT);
        if (n<0) { if (errno==EAGAIN || errno==EINTR) continue; perror("recv");failed=1;break; }
        if (n<20 || (packet[0]>>4)!=4 || packet[9]!=IPPROTO_TCP) continue;
        unsigned ihl=(packet[0]&15)*4;
        if (ihl<20 || (size_t)n<ihl+20) continue;
        unsigned total=((unsigned)packet[2]<<8)|packet[3];
        unsigned frag=((unsigned)packet[6]<<8)|packet[7];
        if (total<ihl+20 || total>(unsigned)n || (frag&0x1fff)) continue;
        unsigned source=((unsigned)packet[ihl]<<8)|packet[ihl+1];
        unsigned dest=((unsigned)packet[ihl+2]<<8)|packet[ihl+3];
        if (source!=80 && dest!=80) continue;
        int match=0;
        for (int i=0;i<argc-4;i++)
            if (!memcmp(packet+12,&targets[i].s_addr,4) || !memcmp(packet+16,&targets[i].s_addr,4)) match=1;
        if (!match) continue;
        if (bytes+total>8UL*1024*1024) { limit=1;break; }
        struct timeval now;gettimeofday(&now,NULL);
        uint32_t record[]={(uint32_t)now.tv_sec,(uint32_t)now.tv_usec,total,total};
        if (fwrite(record,sizeof(record),1,output)!=1 || fwrite(packet,total,1,output)!=1) { perror("packet write");failed=1;break; }
        packets++;bytes+=total;
    }
    if (getsockopt(fd,SOL_PACKET,PACKET_STATISTICS,&stats,&statlen)) { perror("packet stats");failed=1; }
    if (fclose(output)) { perror("capture close");failed=1; }
    close(fd);
    printf("CAPTURE_DONE saved_packets=%lu saved_ip_bytes=%lu socket_packets=%u socket_drops=%u limit_hit=%d failed=%d\n",packets,bytes,stats.tp_packets,stats.tp_drops,limit,failed);
    return failed || limit;
}
