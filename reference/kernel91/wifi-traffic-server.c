/* Two bounded transfers on an explicitly selected IPv4 address. Test files
 * reside in RAM. No credentials, arbitrary paths, or wildcard bind address. */
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <unistd.h>

#define SIZE (4u * 1024u * 1024u)
static int transfer(int socket_fd, int file_fd, int upload)
{
    unsigned char buffer[16384];
    size_t total = 0;
    while (total < SIZE) {
        size_t want = SIZE - total;
        if (want > sizeof(buffer)) want = sizeof(buffer);
        ssize_t n = read(upload ? socket_fd : file_fd, buffer, want);
        if (n <= 0) return -1;
        size_t sent = 0;
        while (sent < (size_t)n) {
            ssize_t m = write(upload ? file_fd : socket_fd, buffer + sent, n - sent);
            if (m <= 0) return -1;
            sent += (size_t)m;
        }
        total += (size_t)n;
    }
    return 0;
}
int main(int argc, char **argv)
{
    struct sockaddr_in address = {.sin_family = AF_INET, .sin_port = htons(18091)};
    if (argc != 2 || inet_pton(AF_INET, argv[1], &address.sin_addr) != 1 ||
        address.sin_addr.s_addr == INADDR_ANY) return 2;
    umask(077);
    signal(SIGPIPE, SIG_IGN);
    alarm(90);
    int listener = socket(AF_INET, SOCK_STREAM | SOCK_CLOEXEC, 0);
    if (listener < 0 || bind(listener, (struct sockaddr *)&address, sizeof(address)) ||
        listen(listener, 2)) { perror("listen"); return 3; }
    puts("WIFI_TRAFFIC_READY"); fflush(stdout);
    unsigned completed = 0;
    for (unsigned i = 0; i < 2; ++i) {
        struct pollfd p = {.fd = listener, .events = POLLIN};
        if (poll(&p, 1, 60000) != 1) return 4;
        int client = accept4(listener, NULL, NULL, SOCK_CLOEXEC);
        char direction;
        if (client < 0 || read(client, &direction, 1) != 1) return 5;
        int upload = direction == 'U';
        unsigned bit = upload ? 2 : 1;
        if ((direction != 'D' && direction != 'U') || (completed & bit)) return 6;
        int file_fd = open(upload ? "/tmp/k91-traffic-upload.bin" : "/tmp/k91-traffic.bin",
            upload ? O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC :
                     O_RDONLY | O_NOFOLLOW | O_CLOEXEC, 0600);
        struct stat st;
        if (file_fd < 0 || fstat(file_fd, &st) || !S_ISREG(st.st_mode) ||
            (!upload && st.st_size != SIZE)) return 7;
        if (transfer(client, file_fd, upload)) return 8;
        close(file_fd);
        if (upload && write(client, "OK", 2) != 2) return 9;
        close(client);
        completed |= bit;
        printf("%s_BYTES=%u\n", upload ? "WIFI_RX" : "WIFI_TX", SIZE);
        fflush(stdout);
    }
    close(listener);
    return completed == 3 ? 0 : 10;
}
