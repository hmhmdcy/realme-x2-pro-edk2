/* Fixed stock standard-word temperature observation.
 * Realme 9668fcdc header defines TEMP=0x06, INTTEMP=0x28; TI SLUUA65E
 * 12.1.4/12.1.21 describe R word values in 0.1 K. This samples only
 * 0x06,0x28,0x08,0x0c,0x14; selector writes contain no register data.
 * Reuses the exact QUP15/client/known bound-driver guard and observer lock.
 * Different readings do not validate TS1 wiring or protection thresholds.
 */
#define main unused_status_reader_main
#include "../kernel80/read-bq28-status.c"
#undef main

int main(int argc, char **argv)
{
    const uint8_t registers[]={0x06,0x28,0x08,0x0c,0x14};
    const char *names[]={"Temperature","InternalTemperature","PackVoltage","InstantCurrent","AverageCurrent"};
    uint8_t selector,data[2];
    unsigned long functions;
    unsigned int i,value;
    int fd,lock,rc=1;
    struct i2c_msg messages[2]={
        {.addr=0x55,.len=1,.buf=&selector},
        {.addr=0x55,.flags=I2C_M_RD,.len=2,.buf=data},
    };
    struct i2c_rdwr_ioctl_data t={.msgs=messages,.nmsgs=2};
    if(argc!=2 || !guard(argv[1])) { fprintf(stderr,"Refusing adapter/client/driver mismatch\n");return 2; }
    lock=open("/tmp/bq28-status-observation.lock",O_CREAT|O_RDWR|O_CLOEXEC|O_NOFOLLOW,0600);
    if(lock<0 || flock(lock,LOCK_EX|LOCK_NB)) { perror("single observer");if(lock>=0)close(lock);return 1; }
    fd=open(argv[1],O_RDONLY|O_CLOEXEC);
    if(fd<0) { perror("adapter");close(lock);return 1; }
    if(ioctl(fd,I2C_FUNCS,&functions)<0 || !(functions&I2C_FUNC_I2C)) goto done;
    puts("fixed_standard_word_selectors=06,28,08,0c,14 MAC_requests=0 register_data_writes=0 retries=0");
    for(i=0;i<sizeof(registers);i++) {
        selector=registers[i];
        if(ioctl(fd,I2C_RDWR,&t)!=2) { perror("standard word transfer");goto done; }
        value=data[0]|((unsigned int)data[1]<<8);
        printf("%s selector=0x%02x bytes=%02x%02x unsigned_word=%u",names[i],selector,data[0],data[1],value);
        if(i<2)printf(" unit=0.1K tentative_C=%.2f",value/10.0-273.15);
        else if(i==2)printf(" unit=mV");
        else printf(" signed_mA=%d",(int)(int16_t)value);
        putchar('\n');fflush(stdout);
        if(i<2 && (value<2000 || value>4500)) { fprintf(stderr,"Temperature outside observation range; stop\n");goto done; }
    }
    rc=0;
done:
    close(fd);close(lock);return rc;
}
