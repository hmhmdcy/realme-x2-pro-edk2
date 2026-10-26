/* Bounded QRTR diagnostic. Publishes service 14 and observes requests only.
 * No request replies, files, shared memory or storage are opened.
 * Decode tables come from linux-msm/rmtfs b30a3eb38f9af283f18dbd3c7755653efc52c094.
 */
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <poll.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include "libqrtr.h"
#include "qmi_rmtfs.h"

static long long milliseconds(void)
{
    struct timespec now;
    if (clock_gettime(CLOCK_MONOTONIC, &now))
        return -1;
    return (long long)now.tv_sec * 1000 + now.tv_nsec / 1000000;
}

int main(void)
{
    long long begin = milliseconds();
    int fd = qrtr_open(14);
    int status = 0;
    unsigned int packets = 0;
    setvbuf(stdout, NULL, _IOLBF, 0);
    if (begin < 0 || fd < 0)
        return 1;
    if (qrtr_publish(fd, 14, 1, 0) < 0) {
        close(fd);
        return 1;
    }
    puts("RMTFS observer published: 20 second deadline; no replies or storage");
    for (;;) {
        long long now = milliseconds();
        struct pollfd pfd = { .fd = fd, .events = POLLIN };
        struct sockaddr_qrtr addr = {0};
        socklen_t addr_len = sizeof(addr);
        struct qrtr_packet packet = {0};
        char buf[4096];
        unsigned int msg_id;
        ssize_t length;
        int ret;
        if (now < 0) { status = 1; break; }
        if (now - begin >= 20000 || packets >= 128)
            break;
        ret = poll(&pfd, 1, (int)(20000 - (now - begin)));
        if (ret < 0 && errno == EINTR) continue;
        if (ret <= 0) { status = ret < 0; break; }
        length = recvfrom(fd, buf, sizeof(buf), MSG_DONTWAIT | MSG_TRUNC,
                          (void *)&addr, &addr_len);
        if (length < 0 && (errno == EAGAIN || errno == EINTR)) continue;
        if (length < 0) { perror("recvfrom"); status = 1; break; }
        if ((size_t)length > sizeof(buf) || addr_len != sizeof(addr)) {
            puts("oversized/invalid packet rejected"); continue;
        }
        packets++;
        ret = qrtr_decode(&packet, buf, (size_t)length, &addr);
        if (ret < 0) { printf("decode_error=%d\n", ret); continue; }
        printf("elapsed_ms=%lld type=%d node=%u port=%u bytes=%zu\n",
               milliseconds() - begin, packet.type, packet.node,
               packet.port, packet.data_len);
        if (packet.type != QRTR_TYPE_DATA) continue;
        ret = qmi_decode_header(&packet, &msg_id);
        if (ret < 0) { printf("qmi_header_error=%d\n", ret); continue; }
        printf("qmi_msg=%u\n", msg_id);
        if (msg_id == QMI_RMTFS_OPEN) {
            struct rmtfs_open_req req = {0};
            unsigned int txn = 0;
            ret = qmi_decode_message(&req, &txn, &packet, QMI_REQUEST,
                                     QMI_RMTFS_OPEN, rmtfs_open_req_ei);
            printf("open_decode=%d txn=%u path=", ret, txn);
            if (ret >= 0) {
                for (size_t i = 0; i < sizeof(req.path) && req.path[i]; i++) {
                    unsigned char c = (unsigned char)req.path[i];
                    if (c >= 32 && c < 127 && c != '\\') putchar(c);
                    else printf("\\x%02x", c);
                }
            }
            putchar('\n');
        }
    }
    printf("observer_done packets=%u status=%d\n", packets, status);
    qrtr_bye(fd, 14, 1, 0);
    close(fd);
    return status;
}
