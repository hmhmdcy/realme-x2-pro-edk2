/* Fixed FirmwareVersion 0x0002 query, also used by the stock gauge driver.
 * Used only after the paired DeviceType observation returned legacy 0xFFA5.
 * No status/FET/protection queries or configuration data writes.
 */
#define main status_reader_main
#include "read-bq28-status.c"
#undef main

int main(int argc, char **argv)
{
    uint8_t data[36];
    unsigned long functions;
    int fd, lock, rc = 1;
    if (argc != 2 || !guard(argv[1])) { fprintf(stderr,"Refusing adapter/client/driver mismatch\n"); return 2; }
    lock = open("/tmp/bq28-status-observation.lock", O_CREAT|O_RDWR|O_CLOEXEC|O_NOFOLLOW,0600);
    if (lock < 0 || flock(lock,LOCK_EX|LOCK_NB)) { perror("single observer"); if(lock>=0) close(lock); return 1; }
    fd = open(argv[1],O_RDONLY|O_CLOEXEC);
    if (fd<0) { perror("adapter"); close(lock); return 1; }
    if (ioctl(fd,I2C_FUNCS,&functions)>=0 && (functions&I2C_FUNC_I2C))
        rc = query(fd,&identity[1],data);
    close(fd); close(lock); return rc;
}
