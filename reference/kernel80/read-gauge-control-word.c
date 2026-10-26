/* Observe the legacy Control() response left by the DeviceType query.
 * Fixed QUP15/0x55; one combined selector/read. No new MAC command.
 */
#define _GNU_SOURCE
#include <fcntl.h>
#include <limits.h>
#include <linux/i2c.h>
#include <linux/i2c-dev.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    char path[PATH_MAX], resolved[PATH_MAX];
    const char *number;
    unsigned long functions;
    uint8_t selector = 0x00, data[2];
    struct i2c_msg messages[2] = {
        {.addr=0x55, .len=1, .buf=&selector},
        {.addr=0x55, .flags=I2C_M_RD, .len=2, .buf=data},
    };
    struct i2c_rdwr_ioctl_data transaction = {.msgs=messages, .nmsgs=2};
    int fd;
    if (argc != 2 || strncmp(argv[1], "/dev/i2c-", 9)) return 2;
    number = argv[1]+9;
    if (!*number || strlen(number)>8 || strspn(number,"0123456789")!=strlen(number)) return 2;
    snprintf(path,sizeof(path),"/sys/bus/i2c/devices/i2c-%s/of_node",number);
    if (!realpath(path,resolved) || strcmp(resolved,"/sys/firmware/devicetree/base/soc@0/geniqup@cc0000/i2c@c94000")) return 2;
    snprintf(path,sizeof(path),"/sys/bus/i2c/devices/%s-0055/of_node",number);
    if (!realpath(path,resolved) || strcmp(resolved,"/sys/firmware/devicetree/base/soc@0/geniqup@cc0000/i2c@c94000/fuel-gauge@55")) return 2;
    snprintf(path,sizeof(path),"/sys/bus/i2c/devices/%s-0055/driver",number);
    if (!realpath(path,resolved) || strcmp(resolved,"/sys/bus/i2c/drivers/bq27xxx-battery")) return 2;
    fd = open(argv[1],O_RDONLY|O_CLOEXEC);
    if (fd<0) { perror("adapter"); return 1; }
    if (ioctl(fd,I2C_FUNCS,&functions)<0 || !(functions&I2C_FUNC_I2C)) { close(fd); return 1; }
    if (ioctl(fd,I2C_RDWR,&transaction)!=2) { perror("Control word read"); close(fd); return 1; }
    close(fd);
    printf("legacy_response adapter=%s address=0x55 register=0x00 word=0x%04x selector_writes=1 command_requests=0\n",argv[1],(unsigned int)data[0]|((unsigned int)data[1]<<8));
    return 0;
}
