/* Fixed OEM short-IC observations. No initialization, config data writes,
 * unlock sequences, OTP/fault reads, scans or forced address ownership.
 * SMBus reads include register-selector write bytes on the I2C wire.
 * O_RDONLY alone would not restrict an ioctl; this program uses READ only.
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

static int read_static_byte(int fd, unsigned char reg)
{
    union i2c_smbus_data value;
    struct i2c_smbus_ioctl_data read = {
        .read_write = I2C_SMBUS_READ,
        .command = reg,
        .size = I2C_SMBUS_BYTE_DATA,
        .data = &value,
    };
    if (reg != 0x00 && reg != 0x02 && reg != 0x03) {
        errno = EPERM;
        return -1;
    }
    if (ioctl(fd, I2C_SMBUS, &read) < 0)
        return -1;
    return value.byte;
}

int main(int argc, char **argv)
{
    const char *number;
    char sys[PATH_MAX], resolved[PATH_MAX];
    unsigned long funcs;
    int fd, identity, threshold, mode;
    if (argc != 2 || strncmp(argv[1], "/dev/i2c-", 9)) {
        fprintf(stderr, "Usage: %s /dev/i2c-BUS (QUP15 only)\n", argv[0]);
        return 2;
    }
    number = argv[1] + 9;
    if (!*number || strspn(number, "0123456789") != strlen(number) || strlen(number) > 8)
        return 2;
    snprintf(sys, sizeof(sys), "/sys/bus/i2c/devices/i2c-%s/of_node", number);
    if (!realpath(sys, resolved) ||
        strcmp(resolved, "/sys/firmware/devicetree/base/soc@0/geniqup@cc0000/i2c@c94000")) {
        fprintf(stderr, "Refusing non-QUP15 adapter\n");
        return 2;
    }
    fd = open(argv[1], O_RDONLY | O_CLOEXEC);
    if (fd < 0) { perror("open"); return 1; }
    if (ioctl(fd, I2C_FUNCS, &funcs) < 0 || !(funcs & I2C_FUNC_SMBUS_READ_BYTE_DATA)) {
        fprintf(stderr, "SMBus read-byte-data unavailable\n");
        close(fd); return 1;
    }
    if (ioctl(fd, I2C_SLAVE, 0x58) < 0) {
        perror("address ownership"); close(fd); return 1;
    }
    printf("SHORT_IC_OBSERVATION adapter=%s of_node=%s address=0x58 data_writes=0 otp_fault_reads=0\n", argv[1], resolved);
    fflush(stdout);
    identity = read_static_byte(fd, 0x00);
    if (identity < 0) { perror("identity read"); close(fd); return 1; }
    printf("reg=0x00 value=0x%02x\n", identity);
    fflush(stdout);
    /* Same factory-family gate as both pinned OEM-derived implementations.
     * A matching nibble is not an exact part identification or safety test. */
    if ((identity & 0xf0) != 0xd0 && (identity & 0xf0) != 0xe0 && (identity & 0xf0) != 0xf0) {
        fprintf(stderr, "Unexpected factory family; no further registers read\n");
        close(fd); return 3;
    }
    threshold = read_static_byte(fd, 0x02);
    if (threshold < 0) { perror("threshold read"); close(fd); return 1; }
    printf("reg=0x02 value=0x%02x\n", threshold);
    fflush(stdout);
    mode = read_static_byte(fd, 0x03);
    if (mode < 0) { perror("mode read"); close(fd); return 1; }
    printf("reg=0x03 value=0x%02x\n", mode);
    printf("completed_static_reads=3 factory_family_matches_source=1\n");
    close(fd);
    return 0;
}
