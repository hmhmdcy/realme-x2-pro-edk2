/* Fixed input observation using the pinned OEM single-byte read protocol.
 * No ADC enabling, fault REG14 read, scans, forced ownership, data writes,
 * reset/watchdog, FET/OTG/NTC changes or GPIO operations. ADC values remain
 * tentative until conversion validity is established independently.
 */
#define _GNU_SOURCE
#include <errno.h>
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
#include <time.h>
#include <unistd.h>

static int fixed_read(int fd, unsigned char reg, unsigned char *value)
{
    if (reg != 0x0b && reg != 0x13 && reg != 0x1c && reg != 0x1d && reg != 0x1e && reg != 0x1f)
        return 1;
    struct i2c_msg messages[2] = {
        {.addr=0x5c, .len=1, .buf=&reg},
        {.addr=0x5c, .flags=I2C_M_RD, .len=1, .buf=value},
    };
    struct i2c_rdwr_ioctl_data transaction = {.msgs=messages, .nmsgs=2};
    errno=0;
    int rc=ioctl(fd,I2C_RDWR,&transaction);
    if(rc!=2) {
        fprintf(stderr,"read reg=0x%02x failed rc=%d errno=%d; no retry\n",reg,rc,errno);
        return 1;
    }
    printf("reg=0x%02x value=0x%02x\n",reg,*value);fflush(stdout);
    return 0;
}

int main(int argc, char **argv)
{
    char path[PATH_MAX],resolved[PATH_MAX];
    const char *number;
    unsigned long functions;
    const unsigned char selectors[]={0x0b,0x13,0x1c,0x1d,0x1e,0x1f,0x13,0x0b};
    unsigned char values[8];
    struct timespec start,end;
    int fd,lock,rc=1;
    unsigned int i;
    if(argc!=2 || strncmp(argv[1],"/dev/i2c-",9)) return 2;
    number=argv[1]+9;
    if(!*number || strlen(number)>8 || strspn(number,"0123456789")!=strlen(number)) return 2;
    snprintf(path,sizeof(path),"/sys/bus/i2c/devices/i2c-%s/of_node",number);
    if(!realpath(path,resolved) || strcmp(resolved,"/sys/firmware/devicetree/base/soc@0/geniqup@8c0000/i2c@884000")) {
        fputs("Refusing non-QUP1 adapter\n",stderr);return 2;
    }
    lock=open("/tmp/mp2650-observation.lock",O_CREAT|O_RDWR|O_CLOEXEC|O_NOFOLLOW,0600);
    if(lock<0 || flock(lock,LOCK_EX|LOCK_NB)) {
        perror("single observer");if(lock>=0)close(lock);return 1;
    }
    fd=open(argv[1],O_RDONLY|O_CLOEXEC);
    if(fd<0) {perror("adapter");close(lock);return 1;}
    if(ioctl(fd,I2C_FUNCS,&functions)<0 || !(functions&I2C_FUNC_I2C)) goto done;
    if(ioctl(fd,I2C_SLAVE,0x5c)<0) {perror("address ownership");goto done;}
    puts("MP2650_FIXED_INPUT selectors=0b,13,1c,1d,1e,1f,13,0b address=5c configuration_data_writes=0 fault_reads=0 ADC_enable=0 retries=0");
    if(clock_gettime(CLOCK_MONOTONIC,&start)) goto done;
    for(i=0;i<8;i++) if(fixed_read(fd,selectors[i],&values[i])) goto done;
    if(clock_gettime(CLOCK_MONOTONIC,&end)) goto done;
    unsigned int voltage_code=((unsigned int)values[3]<<2)|(values[2]>>6);
    unsigned int current_code=((unsigned int)values[5]<<2)|(values[4]>>6);
    printf("OEM_scale VIN_code=%u tentative_mV=%u IIN_code=%u tentative_uA=%u\n",voltage_code,voltage_code*25,current_code,current_code*6250);
    printf("status_boundary_equal=%u config_boundary_equal=%u independent_single_byte_pairs=1 ADC_freshness_verified=0\n",values[1]==values[6],values[0]==values[7]);
    printf("query_span_ns=%lld\n",(long long)(end.tv_sec-start.tv_sec)*1000000000LL+end.tv_nsec-start.tv_nsec);
    rc=0;
done:
    close(fd);close(lock);return rc;
}
