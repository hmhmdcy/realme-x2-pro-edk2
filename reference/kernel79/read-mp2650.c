/* Fixed-address MP2650 register observations. MPS Rev1.0 Figure16 single reads.
 * No data writes, scans, fault-register reads, ADC enable, watchdog service,
 * reset, OTG/BATTFET changes, GPIO operations or arbitrary register selection.
 * O_RDONLY alone is not a safety guarantee for I2C_RDWR: each write message is
 * explicitly restricted to the ONE register-selector byte of a combined read.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <linux/i2c.h>
#include <linux/i2c-dev.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>

static const unsigned char registers[] = {
    0x08, 0x09, 0x0a, 0x07, 0x00, 0x01,
    0x02, 0x03, 0x04, 0x0f, 0x0b, 0x13,
};

int main(int argc, char **argv)
{
    char sys[PATH_MAX], resolved[PATH_MAX];
    const char *number;
    unsigned long funcs;
    unsigned int i;
    int fd, rc;

    if (argc != 2 || strncmp(argv[1], "/dev/i2c-", 9)) {
        fprintf(stderr, "Usage: %s /dev/i2c-BUS (QUP1 only)\n", argv[0]);
        return 2;
    }
    number = argv[1]+9;
    if (!*number || strspn(number, "0123456789") != strlen(number) || strlen(number) > 8) {
        fprintf(stderr, "Invalid adapter path\n");
        return 2;
    }
    snprintf(sys, sizeof(sys), "/sys/bus/i2c/devices/i2c-%s/of_node", number);
    if (!realpath(sys, resolved) ||
        strcmp(resolved, "/sys/firmware/devicetree/base/soc@0/geniqup@8c0000/i2c@884000")) {
        fprintf(stderr, "Refusing non-QUP1 adapter\n");
        return 2;
    }
    fd = open(argv[1], O_RDONLY | O_CLOEXEC);
    if (fd < 0) { perror("open"); return 1; }
    if (ioctl(fd, I2C_FUNCS, &funcs) < 0 || !(funcs & I2C_FUNC_I2C)) {
        fprintf(stderr, "Combined I2C reads unavailable\n");
        close(fd); return 1;
    }
    /* I2C_RDWR otherwise bypasses the address-in-use check. Never FORCE. */
    if (ioctl(fd, I2C_SLAVE, 0x5c) < 0) {
        perror("address ownership"); close(fd); return 1;
    }
    printf("MP2650_OBSERVATION adapter=%s of_node=%s address=0x5c transactions=12 data_writes=0 fault_reads=0\n", argv[1], resolved);
    fflush(stdout);
    for (i = 0; i < sizeof(registers)/sizeof(registers[0]); i++) {
        unsigned char selector = registers[i], value;
        struct i2c_msg messages[2] = {
            {.addr=0x5c, .flags=0, .len=1, .buf=&selector},
            {.addr=0x5c, .flags=I2C_M_RD, .len=1, .buf=&value},
        };
        struct i2c_rdwr_ioctl_data transaction = {.msgs=messages, .nmsgs=2};
        errno = 0;
        rc = ioctl(fd, I2C_RDWR, &transaction);
        if (rc != 2) {
            fprintf(stderr, "read reg=0x%02x failed rc=%d errno=%d; stopping without retry\n", selector, rc, errno);
            close(fd); return 1;
        }
        printf("reg=0x%02x value=0x%02x\n", selector, value);
        fflush(stdout);
    }
    close(fd);
    return 0;
}
