// Real QRTR packets; uses a separate TFTP instance for the candidate.
#define _GNU_SOURCE
#include <arpa/inet.h>
#include <assert.h>
#include <endian.h>
#include <errno.h>
#include <libqrtr.h>
#include <poll.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

static struct sockaddr_qrtr server;
static unsigned int transactions, compared_bytes;
static uint16_t get16(const unsigned char *b) { return (uint16_t)b[0] * 256 + b[1]; }
static void put16(unsigned char *b, uint16_t n) { b[0] = n >> 8; b[1] = n; }
static ssize_t receive(int fd, unsigned char *buf, size_t size, struct sockaddr_qrtr *peer)
{
    for (unsigned int i = 0; i < 50; i++) {
        struct pollfd p = {.fd = fd, .events = POLLIN};
        assert(poll(&p, 1, 2000) == 1);
        socklen_t len = sizeof(*peer);
        ssize_t n = recvfrom(fd, buf, size, MSG_TRUNC, (void *)peer, &len);
        assert(n >= 0 && (size_t)n <= size && len == sizeof(*peer));
        if (peer->sq_port == QRTR_PORT_CTRL) continue;
        return n;
    }
    abort();
}
static void send_packet(int fd, const struct sockaddr_qrtr *peer, const void *data, size_t size)
{
    assert(sendto(fd, data, size, 0, (const void *)peer, sizeof(*peer)) == (ssize_t)size);
}
static void lookup(unsigned int instance)
{
    int fd = qrtr_open(0); assert(fd >= 0);
    struct sockaddr_qrtr local;
    socklen_t size = sizeof(local);
    assert(!getsockname(fd, (void *)&local, &size));
    assert(qrtr_new_lookup(fd, 4096, 1, instance) >= 0);
    for (unsigned int i = 0; i < 30; i++) {
        struct pollfd p = {.fd = fd, .events = POLLIN};
        assert(poll(&p, 1, 2000) == 1);
        struct sockaddr_qrtr peer;
        struct qrtr_ctrl_pkt packet;
        socklen_t n = sizeof(peer);
        ssize_t got = recvfrom(fd, &packet, sizeof(packet), 0, (void *)&peer, &n);
        assert(got == sizeof(packet));
        if (le32toh(packet.cmd) != QRTR_TYPE_NEW_SERVER ||
            le32toh(packet.server.service) != 4096 ||
            le32toh(packet.server.instance) != ((instance << 8) | 1) ||
            le32toh(packet.server.node) != local.sq_node) continue;
        server = (struct sockaddr_qrtr){.sq_family = AF_QIPCRTR,
            .sq_node = le32toh(packet.server.node), .sq_port = le32toh(packet.server.port)};
        close(fd); return;
    }
    abort();
}
static size_t string(unsigned char *buffer, size_t at, const char *s)
{
    size_t n = strlen(s) + 1; assert(at + n < 1024); memcpy(buffer + at, s, n); return at + n;
}
static size_t option(unsigned char *buffer, size_t at, const char *key, size_t value)
{
    char text[40]; snprintf(text, sizeof(text), "%zu", value);
    return string(buffer, string(buffer, at, key), text);
}
static size_t request(unsigned char *buffer, unsigned int opcode, const char *path,
                      size_t count, unsigned int block, unsigned int window,
                      size_t seek, int options, int range)
{
    put16(buffer, opcode);
    size_t n = string(buffer, string(buffer, 2, path), "octet");
    if (options) {
        n = option(buffer, n, "blksize", block);
        n = option(buffer, n, "wsize", window);
        n = option(buffer, n, "tsize", opcode == 2 ? count : 0);
        if (seek) n = option(buffer, n, "seek", seek);
        if (range) n = option(buffer, n, "rsize", count);
    }
    return n;
}
static void ack(int fd, const struct sockaddr_qrtr *peer, unsigned int block)
{
    unsigned char packet[4]; put16(packet, 4); put16(packet + 2, block);
    send_packet(fd, peer, packet, sizeof(packet));
}
static void write_file(const char *path, const unsigned char *data, size_t count,
                       unsigned int block_size, unsigned int window, size_t seek,
                       int options, int denied)
{
    unsigned char packet[2048]; struct sockaddr_qrtr peer, response;
    int fd = qrtr_open(0); assert(fd >= 0);
    size_t n = request(packet, 2, path, count, block_size, window, seek, options, 0);
    send_packet(fd, &server, packet, n);
    ssize_t got = receive(fd, packet, sizeof(packet), &peer);
    assert(got >= 4 && peer.sq_node == server.sq_node);
    if (denied) {
        assert(get16(packet) == 5 && get16(packet + 2) == 2);
        close(fd); transactions++; return;
    }
    assert(get16(packet) == (options ? 6 : 4));
    if (!options) assert(get16(packet + 2) == 0);
    size_t offset = 0;
    for (unsigned int block = 1; ; block++) {
        size_t payload = count - offset;
        if (payload > block_size) payload = block_size;
        put16(packet, 3); put16(packet + 2, block);
        memcpy(packet + 4, data + offset, payload);
        send_packet(fd, &peer, packet, payload + 4);
        offset += payload;
        if (block % window == 0 || payload < block_size) {
            got = receive(fd, packet, sizeof(packet), &response);
            assert(got == 4 && response.sq_node == peer.sq_node && response.sq_port == peer.sq_port);
            assert(get16(packet) == 4 && get16(packet + 2) == block);
        }
        if (payload < block_size) break;
    }
    close(fd); transactions++;
}
static void read_file(const char *path, const unsigned char *expected, size_t count,
                      unsigned int block_size, unsigned int window, size_t seek,
                      int options, int range)
{
    unsigned char packet[2048]; struct sockaddr_qrtr peer, response;
    int fd = qrtr_open(0); assert(fd >= 0);
    size_t n = request(packet, 1, path, count, block_size, window, seek, options, range);
    send_packet(fd, &server, packet, n);
    ssize_t got = receive(fd, packet, sizeof(packet), &peer);
    assert(got >= 2 && peer.sq_node == server.sq_node);
    if (options) { assert(get16(packet) == 6); ack(fd, &peer, 0); }
    size_t offset = 0;
    for (unsigned int block = 1; ; block++) {
        if (options || block != 1) {
            got = receive(fd, packet, sizeof(packet), &response);
            assert(response.sq_node == peer.sq_node && response.sq_port == peer.sq_port);
        }
        assert(got >= 4 && get16(packet) == 3 && get16(packet + 2) == block);
        size_t payload = (size_t)got - 4;
        assert(payload <= block_size && payload <= count - offset);
        assert(!memcmp(packet + 4, expected + offset, payload)); offset += payload;
        if (block % window == 0 || payload < block_size) ack(fd, &peer, block);
        if (payload < block_size) break;
    }
    assert(offset == count); compared_bytes += count;
    close(fd); transactions++;
}
int main(int argc, char **argv)
{
    assert(argc == 3); alarm(30);
    unsigned int instance = (unsigned int)strtoul(argv[1], NULL, 10);
    assert(instance == 0 || instance == 206); lookup(instance);
    unsigned char data[10000]; for (size_t i = 0; i < sizeof(data); i++) data[i] = (unsigned char)(i * 29 + 7);
    const char *path = "/readwrite/samurai-validation206/work.tmp";
    if (!strcmp(argv[2], "deny")) {
        write_file(path, data, 17, 512, 1, 0, 0, 1);
    } else {
        assert(!strcmp(argv[2], "pass"));
        write_file(path, data, 6145, 1024, 4, 0, 1, 0);
        read_file(path, data, 6145, 1024, 4, 0, 1, 0);
        read_file(path, data + 500, 2000, 1024, 4, 500, 1, 1);
        write_file(path, data, 8192, 1024, 4, 0, 1, 0);
        read_file(path, data, 8192, 1024, 4, 0, 1, 0);
        read_file(path, data, 2048, 1024, 4, 0, 1, 1);
        write_file(path, data, 1025, 512, 1, 0, 0, 0);
        read_file(path, data, 1025, 512, 1, 0, 0, 0);
        write_file(path, (const unsigned char *)"XYZ", 3, 1024, 1, 17, 1, 0);
        memcpy(data + 17, "XYZ", 3);
        read_file(path, data, 1025, 512, 1, 0, 0, 0);
        write_file(path, data, 0, 512, 1, 0, 0, 0);
        read_file(path, data, 0, 512, 1, 0, 0, 0);
        write_file("/readonly/firmware/image/fixture", data, 3, 512, 1, 0, 0, 1);
    }
    printf("{\"qrtr_transactions\":%u,\"readback_bytes_compared\":%u,\"instance\":%u}\n", transactions, compared_bytes, instance);
    return 0;
}
