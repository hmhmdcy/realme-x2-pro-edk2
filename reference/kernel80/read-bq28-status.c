/* BQ28Z610 bounded MAC observations: TI SLUUA65E 12.1.28 and 12.2.
 * Command requests change the response buffer, not charging configuration.
 * Only the fixed R commands below are allowed; no arbitrary opcode, unseal,
 * reset, calibration, protection/FET toggle, checksum/length or NVM writes.
 * I2C_RDWR does not enforce O_RDONLY or address ownership. This tool explicitly
 * allows the audited bq27xxx driver, whose BQ28Z610 path reads standard words
 * and does not use the MAC response buffer. Do not run with another driver.
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
#include <sys/file.h>
#include <sys/ioctl.h>
#include <unistd.h>

struct query { uint16_t command; unsigned int payload; const char *name; };
static const struct query identity[] = {
    {0x0001, 2, "DeviceType"}, {0x0002, 11, "FirmwareVersion"},
};
static const struct query status[] = {
    {0x0050, 4, "SafetyAlert"}, {0x0051, 4, "SafetyStatus"},
    {0x0052, 4, "PFAlert"}, {0x0053, 4, "PFStatus"},
    {0x0054, 4, "OperationStatus"}, {0x0055, 2, "ChargingStatus"},
    {0x0057, 2, "ManufacturingStatus"},
    {0x0071, 32, "DAStatus1"}, {0x0072, 14, "DAStatus2"},
};

static int validate(const struct query *q, const uint8_t data[36])
{
    unsigned int i, sum = 0;
    if (data[0] != (q->command & 255) || data[1] != (q->command >> 8))
        return 1;
    if (data[35] != q->payload + 4 || data[35] < 5 || data[35] > 36)
        return 2;
    for (i = 0; i < data[35]-2U; i++) sum += data[i];
    if (data[34] != (uint8_t)(255U - sum)) return 3;
    return 0;
}

static void checksum(uint8_t data[36], const struct query *q)
{
    unsigned int i, sum = 0;
    data[0] = q->command & 255; data[1] = q->command >> 8;
    data[35] = q->payload + 4;
    for (i = 0; i < data[35]-2U; i++) sum += data[i];
    data[34] = 255U - sum;
}

static int selftest(void)
{
    uint8_t data[36] = {0};
    struct query q = {0x0071, 32, "test"};
    unsigned int i;
    for (i = 2; i < 34; i++) data[i] = i * 17U;
    checksum(data, &q);
    if (validate(&q, data)) return 1;
    data[0] ^= 1;
    if (validate(&q, data) != 1) return 1;
    data[0] ^= 1; data[35] = 255;
    if (validate(&q, data) != 2) return 1;
    checksum(data, &q); data[2] ^= 1;
    if (validate(&q, data) != 3) return 1;
    q = identity[0]; memset(data, 0, sizeof(data));
    data[2] = 0x10; data[3] = 0x26; checksum(data, &q);
    if (validate(&q, data)) return 1;
    puts("SELFTEST valid32, wrong_echo, invalid_length, bad_checksum, valid2 PASS; hardware_access=0");
    return 0;
}

static int path_matches(const char *path, const char *expected)
{
    char resolved[PATH_MAX];
    return realpath(path, resolved) && !strcmp(resolved, expected);
}

static int guard(const char *adapter)
{
    char path[PATH_MAX], compatible[64] = {0};
    const char *number;
    int fd;
    ssize_t size;
    if (strncmp(adapter, "/dev/i2c-", 9)) return 0;
    number = adapter + 9;
    if (!*number || strlen(number) > 8 || strspn(number, "0123456789") != strlen(number)) return 0;
    snprintf(path, sizeof(path), "/sys/bus/i2c/devices/i2c-%s/of_node", number);
    if (!path_matches(path, "/sys/firmware/devicetree/base/soc@0/geniqup@cc0000/i2c@c94000")) return 0;
    snprintf(path, sizeof(path), "/sys/bus/i2c/devices/%s-0055/of_node", number);
    if (!path_matches(path, "/sys/firmware/devicetree/base/soc@0/geniqup@cc0000/i2c@c94000/fuel-gauge@55")) return 0;
    snprintf(path, sizeof(path), "/sys/bus/i2c/devices/%s-0055/driver", number);
    if (!path_matches(path, "/sys/bus/i2c/drivers/bq27xxx-battery")) return 0;
    snprintf(path, sizeof(path), "/sys/bus/i2c/devices/%s-0055/of_node/compatible", number);
    fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) return 0;
    size = read(fd, compatible, sizeof(compatible)); close(fd);
    return size == (ssize_t)sizeof("ti,bq28z610") && !memcmp(compatible, "ti,bq28z610", sizeof("ti,bq28z610"));
}

static int query(int fd, const struct query *q, uint8_t data[36])
{
    /* TRM recommends 0x00/01 to request R commands; never write 0x60/61. */
    uint8_t request[3] = {0x00, q->command & 255, q->command >> 8};
    uint8_t selector = 0x3e;
    struct i2c_msg write = {.addr=0x55, .len=3, .buf=request};
    struct i2c_rdwr_ioctl_data transaction = {.msgs=&write, .nmsgs=1};
    struct i2c_msg messages[2] = {
        {.addr=0x55, .len=1, .buf=&selector},
        {.addr=0x55, .flags=I2C_M_RD, .len=36, .buf=data},
    };
    unsigned int i;
    int error;
    if (ioctl(fd, I2C_RDWR, &transaction) != 1) { perror("MAC request"); return 1; }
    if (usleep(10000)) { perror("MAC wait"); return 1; }
    transaction.msgs = messages; transaction.nmsgs = 2;
    if (ioctl(fd, I2C_RDWR, &transaction) != 2) { perror("MAC response"); return 1; }
    error = validate(q, data);
    printf("%s command=0x%04x request=00%02x%02x response=", q->name,
           q->command, request[1], request[2]);
    for (i = 0; i < 36; i++) printf("%02x", data[i]);
    printf(" payload=%u length=%u checksum=%02x validation=%d\n", q->payload, data[35], data[34], error);
    fflush(stdout);
    if (error) fprintf(stderr, "Invalid response; stopping without retry (1=echo,2=length,3=checksum)\n");
    return error != 0;
}

int main(int argc, char **argv)
{
    uint8_t data[36];
    unsigned long functions;
    unsigned int i;
    int fd, lock, rc = 1;
    if (argc == 2 && !strcmp(argv[1], "--selftest")) return selftest();
    if (argc != 3 || (strcmp(argv[2], "identity") && strcmp(argv[2], "status"))) {
        fprintf(stderr, "Usage: %s /dev/i2c-BUS identity|status OR --selftest\n", argv[0]); return 2;
    }
    if (!guard(argv[1])) { fprintf(stderr, "Refusing adapter/client/driver mismatch\n"); return 2; }
    lock = open("/tmp/bq28-status-observation.lock", O_CREAT | O_RDWR | O_CLOEXEC | O_NOFOLLOW, 0600);
    if (lock < 0 || flock(lock, LOCK_EX | LOCK_NB)) { perror("single observer"); if (lock >= 0) close(lock); return 1; }
    fd = open(argv[1], O_RDONLY | O_CLOEXEC);
    if (fd < 0) { perror("adapter"); close(lock); return 1; }
    if (ioctl(fd, I2C_FUNCS, &functions) < 0 || !(functions & I2C_FUNC_I2C)) {
        fprintf(stderr, "I2C transfers unavailable\n"); goto done;
    }
    printf("BQ28Z610_MAC_OBSERVATION adapter=%s address=0x55 mode=%s; R_queries_only=1 settings_writes=0 retries=0\n", argv[1], argv[2]);
    for (i = 0; i < sizeof(identity)/sizeof(identity[0]); i++) {
        if (query(fd, &identity[i], data)) goto done;
        if (!i && (data[2] != 0x10 || data[3] != 0x26)) {
            fprintf(stderr, "DeviceType differs from 0x2610; stop for manual review\n"); goto done;
        }
    }
    if (!strcmp(argv[2], "status"))
        for (i = 0; i < sizeof(status)/sizeof(status[0]); i++)
            if (query(fd, &status[i], data)) goto done;
    rc = 0;
done:
    close(fd); close(lock); return rc;
}
