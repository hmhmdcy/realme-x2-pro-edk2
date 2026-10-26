/* Read only documented standard words from BQ28Z610 at fixed address 0x55.
 * No Control/MAC commands, unseal, NVM, reset, calibration or charge writes.
 * I2C writes contain only the one-byte register selector in a combined read.
 */
#include <errno.h>
#include <fcntl.h>
#include <linux/i2c.h>
#include <linux/i2c-dev.h>
#include <stdint.h>
#include <stdio.h>
#include <sys/ioctl.h>
#include <unistd.h>

struct standard_word { const char *name; uint8_t reg; };
static const struct standard_word words[] = {
    { "temperature", 0x06 }, { "pack_voltage", 0x08 }, { "flags", 0x0a },
    { "remaining_capacity", 0x10 }, { "full_capacity", 0x12 },
    { "average_current", 0x14 }, { "time_to_empty", 0x16 },
    { "time_to_full", 0x18 }, { "average_power", 0x22 },
    { "cycle_count", 0x2a }, { "state_of_charge", 0x2c },
    { "design_capacity", 0x3c },
};
int main(int argc, char **argv)
{
    unsigned int i;
    int fd;
    if (argc != 2) { fprintf(stderr, "Usage: %s /dev/i2c-BUS\n", argv[0]); return 2; }
    fd = open(argv[1], O_RDONLY | O_CLOEXEC);
    if (fd < 0) { perror("open"); return 1; }
    for (i = 0; i < sizeof(words)/sizeof(words[0]); i++) {
        uint8_t reg = words[i].reg, data[2];
        struct i2c_msg messages[2] = {
            { .addr = 0x55, .flags = 0, .len = 1, .buf = &reg },
            { .addr = 0x55, .flags = I2C_M_RD, .len = 2, .buf = data },
        };
        struct i2c_rdwr_ioctl_data transaction = { .msgs = messages, .nmsgs = 2 };
        if (ioctl(fd, I2C_RDWR, &transaction) != 2) {
            fprintf(stderr, "read 0x%02x failed: errno=%d\n", reg, errno);
            close(fd); return 1;
        }
        printf("%s reg=0x%02x value=%u hex=%02x%02x\n", words[i].name,
               reg, (unsigned int)data[0] | ((unsigned int)data[1]<<8), data[1], data[0]);
    }
    close(fd);
    return 0;
}
