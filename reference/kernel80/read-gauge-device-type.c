/* One fixed DeviceType (0x0001) query, with legacy word and MAC block reads.
 * Compare the stock legacy protocol with TI SLUUA65E extended response.
 * No firmware/protection query, arbitrary opcode, unseal or configuration data.
 * The bound bq27xxx BQ28Z610 path has been audited not to use MAC commands.
 */
#define main status_reader_main
#include "read-bq28-status.c"
#undef main

int main(int argc, char **argv)
{
    uint8_t request[3] = {0x00, 0x01, 0x00}, selector = 0x00;
    uint8_t legacy[2], block[36];
    struct i2c_msg write = {.addr=0x55, .len=3, .buf=request};
    struct i2c_rdwr_ioctl_data transaction = {.msgs=&write, .nmsgs=1};
    struct i2c_msg messages[2] = {
        {.addr=0x55, .len=1, .buf=&selector},
        {.addr=0x55, .flags=I2C_M_RD, .len=2, .buf=legacy},
    };
    unsigned long functions;
    unsigned int i;
    int fd, lock, rc = 1, validation;
    if (argc != 2 || !guard(argv[1])) { fprintf(stderr,"Refusing adapter/client/driver mismatch\n"); return 2; }
    lock = open("/tmp/bq28-status-observation.lock", O_CREAT|O_RDWR|O_CLOEXEC|O_NOFOLLOW,0600);
    if (lock < 0 || flock(lock,LOCK_EX|LOCK_NB)) { perror("single observer"); if(lock>=0) close(lock); return 1; }
    fd = open(argv[1],O_RDONLY|O_CLOEXEC);
    if (fd<0) { perror("adapter"); close(lock); return 1; }
    if (ioctl(fd,I2C_FUNCS,&functions)<0 || !(functions&I2C_FUNC_I2C)) goto done;
    if (ioctl(fd,I2C_RDWR,&transaction)!=1) { perror("DeviceType request"); goto done; }
    if (usleep(1000)) goto done;
    transaction.msgs=messages; transaction.nmsgs=2;
    if (ioctl(fd,I2C_RDWR,&transaction)!=2) { perror("legacy response"); goto done; }
    printf("DeviceType request=000100 legacy_word=0x%04x delay_us=1000 retries=0\n",(unsigned int)legacy[0]|((unsigned int)legacy[1]<<8));
    selector=0x3e; messages[1].len=36; messages[1].buf=block;
    if (ioctl(fd,I2C_RDWR,&transaction)!=2) { perror("extended response"); goto done; }
    validation=validate(&identity[0],block);
    printf("DeviceType extended_response=");
    for (i=0;i<36;i++) printf("%02x",block[i]);
    printf(" validation=%d\n",validation);
    rc=validation ? 1 : 0;
done:
    close(fd); close(lock); return rc;
}
