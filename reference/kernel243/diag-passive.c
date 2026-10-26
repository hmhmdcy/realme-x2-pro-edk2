/* Bounded DIAG transport discovery. Only QRTR namespace announcements are sent.
 * No DIAG commands, masks, mode changes, RF controls, storage or NV operations.
 * Wire values follow linux-msm/diag router/peripheral-qrtr.c (BSD-3-Clause).
 */
#define _GNU_SOURCE
#include <endian.h>
#include <errno.h>
#include <linux/qrtr.h>
#include <poll.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>

static volatile sig_atomic_t stopped;
static void stop(int signum) { (void)signum; stopped = 1; }
static int64_t now_ms(void)
{
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) return -1;
    return (int64_t)t.tv_sec * 1000 + t.tv_nsec / 1000000;
}
static int ns(int fd, uint32_t operation, uint32_t instance)
{
    struct sockaddr_qrtr local = {0};
    socklen_t length = sizeof(local);
    if (getsockname(fd, (void *)&local, &length) || length != sizeof(local)) return -1;
    struct qrtr_ctrl_pkt pkt = {0};
    pkt.cmd = htole32(operation);
    pkt.server.service = htole32(4097);
    pkt.server.instance = htole32(instance); /* DIAG uses unshifted instances. */
    pkt.server.node = htole32(local.sq_node);
    pkt.server.port = htole32(local.sq_port);
    local.sq_port = QRTR_PORT_CTRL;
    return sendto(fd, &pkt, sizeof(pkt), 0, (void *)&local, sizeof(local)) == sizeof(pkt) ? 0 : -1;
}
int main(void)
{
    int fds[4] = {-1,-1,-1,-1}, published[3] = {0};
    const uint32_t instances[3] = {0,2,4};
    const char *names[4] = {"control","data","dci","lookup"};
    int rc=0, deleted=0, closed=0;
    unsigned int packets=0, control_packets=0, data_packets=0;
    size_t bytes=0;
    signal(SIGINT,stop); signal(SIGTERM,stop); setvbuf(stdout,NULL,_IOLBF,0);
    int64_t began=now_ms();
    if (began<0) return 1;
    for (int i=0;i<4;i++) {
        fds[i]=socket(AF_QIPCRTR,SOCK_DGRAM|SOCK_CLOEXEC,0);
        if(fds[i]<0){rc=1;goto cleanup;}
        /* Bind before constructing NEW_SERVER, so its advertised port is real. */
        struct sockaddr_qrtr local={0};socklen_t size=sizeof(local);
        if(getsockname(fds[i],(void *)&local,&size) || size!=sizeof(local)){perror("getsockname");rc=1;goto cleanup;}
        local.sq_port=0;
        if(bind(fds[i],(void *)&local,sizeof(local))){perror("bind");rc=1;goto cleanup;}
    }
    /* Look up existing and newly appearing modem command endpoints. */
    if(ns(fds[3],QRTR_TYPE_NEW_LOOKUP,0)){rc=1;goto cleanup;}
    for(int i=0;i<3;i++) {
        if(ns(fds[i],QRTR_TYPE_NEW_SERVER,instances[i])){rc=1;goto cleanup;}
        published[i]=1;
    }
    puts("{\"kind\":\"published\",\"service\":4097,\"instances\":[0,2,4],\"diagnostic_payloads_sent\":0}");
    while(!stopped && packets<512 && bytes<2*1024*1024) {
        int64_t remaining=20000-(now_ms()-began);
        if(remaining<=0) break;
        struct pollfd pollfds[4];
        for(int i=0;i<4;i++)pollfds[i]=(struct pollfd){.fd=fds[i],.events=POLLIN};
        int ret=poll(pollfds,4,(int)remaining);
        if(ret<0 && errno==EINTR)continue;
        if(ret<=0){if(ret<0)rc=1;break;}
        for(int i=0;i<4;i++) {
            if(!(pollfds[i].revents&POLLIN))continue;
            uint8_t data[32768];struct sockaddr_qrtr peer={0};socklen_t length=sizeof(peer);
            ssize_t count=recvfrom(fds[i],data,sizeof(data),MSG_DONTWAIT|MSG_TRUNC,(void *)&peer,&length);
            if(count<0 && (errno==EAGAIN || errno==EINTR))continue;
            if(count<0 || length!=sizeof(peer) || (size_t)count>sizeof(data)){rc=1;goto cleanup;}
            packets++;bytes+=(size_t)count;
            if(peer.sq_port!=QRTR_PORT_CTRL){if(i==0)control_packets++;else if(i==1)data_packets++;}
            printf("{\"kind\":\"packet\",\"channel\":\"%s\",\"elapsed_ms\":%lld,\"node\":%u,\"port\":%u,\"bytes\":%zd,\"hex\":\"",names[i],(long long)(now_ms()-began),peer.sq_node,peer.sq_port,count);
            for(ssize_t j=0;j<count;j++)printf("%02x",data[j]);
            puts("\"}");
        }
    }
cleanup:
    for(int i=0;i<3;i++)if(published[i]){if(ns(fds[i],QRTR_TYPE_DEL_SERVER,instances[i]))rc=1;else deleted++;}
    for(int i=0;i<4;i++)if(fds[i]>=0){if(close(fds[i]))rc=1;else closed++;}
    printf("{\"kind\":\"cleanup\",\"exit_code\":%d,\"servers_removed\":%d,\"sockets_closed\":%d,\"packets\":%u,\"control_packets\":%u,\"data_packets\":%u,\"received_bytes\":%zu,\"diagnostic_payloads_sent\":0,\"interrupted\":%s}\n",rc,deleted,closed,packets,control_packets,data_packets,bytes,stopped?"true":"false");
    return rc;
}
