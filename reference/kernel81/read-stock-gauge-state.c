/* Fixed stock bq8z610_sealed()/bq8z610_check_gauge_enable() observations.
 * Realme 9668fcdc source uses 3E 54 00 and 3E 57 00, then four bytes at 3E.
 * Guard the exact session80 legacy/type/FW responses before these stock R
 * queries. No unseal, seal, enable/disable, calibration or data-flash writes.
 * This does not establish full safety-threshold or thermistor compatibility.
 */
#define main unused_status_reader_main
#include "../kernel80/read-bq28-status.c"
#undef main

static int transfer(int fd, struct i2c_msg *m, unsigned int count)
{
    struct i2c_rdwr_ioctl_data t={.msgs=m,.nmsgs=count};
    if(ioctl(fd,I2C_RDWR,&t)!=(int)count) { perror("fixed stock transfer");return 1; }
    return 0;
}

int main(int argc, char **argv)
{
    const struct query states[]={{0x0054,4,"stock_seal_state"},{0x0057,2,"stock_gauge_enabled"}};
    const uint8_t expected_fw[11]={0x27,0x19,0x00,0x04,0x00,0x06,0x00,0x03,0x85,0x02,0x00};
    uint8_t request[3]={0x00,0x01,0x00}, selector=0x00, legacy[2], block[36], short_read[4];
    struct i2c_msg write={.addr=0x55,.len=3,.buf=request};
    struct i2c_msg messages[2]={
        {.addr=0x55,.len=1,.buf=&selector},
        {.addr=0x55,.flags=I2C_M_RD,.len=2,.buf=legacy},
    };
    unsigned long functions;
    unsigned int i,j;
    int fd,lock,rc=1;
    if(argc!=2 || !guard(argv[1])) { fprintf(stderr,"Refusing adapter/client/driver mismatch\n");return 2; }
    lock=open("/tmp/bq28-status-observation.lock",O_CREAT|O_RDWR|O_CLOEXEC|O_NOFOLLOW,0600);
    if(lock<0 || flock(lock,LOCK_EX|LOCK_NB)) { perror("single observer");if(lock>=0)close(lock);return 1; }
    fd=open(argv[1],O_RDONLY|O_CLOEXEC);
    if(fd<0) { perror("adapter");close(lock);return 1; }
    if(ioctl(fd,I2C_FUNCS,&functions)<0 || !(functions&I2C_FUNC_I2C)) goto done;
    if(transfer(fd,&write,1) || usleep(1000) || transfer(fd,messages,2)) goto done;
    printf("identity legacy_word=0x%04x\n",(unsigned int)legacy[0]|((unsigned int)legacy[1]<<8));
    if(legacy[0]!=0xa5 || legacy[1]!=0xff) goto done;
    selector=0x3e;messages[1].buf=block;messages[1].len=36;
    if(transfer(fd,messages,2) || validate(&identity[0],block) || block[2]!=0x19 || block[3]!=0x27) goto done;
    if(query(fd,&identity[1],block) || memcmp(block+2,expected_fw,11)) goto done;
    puts("session80_exact_identity_and_firmware_guard=PASS; queries=0054,0057; retries=0 settings_writes=0");
    for(i=0;i<sizeof(states)/sizeof(states[0]);i++) {
        request[0]=0x3e;request[1]=states[i].command&255;request[2]=states[i].command>>8;
        if(transfer(fd,&write,1) || usleep(i ? 1000000 : 10000)) goto done;
        selector=0x3e;messages[1].buf=short_read;messages[1].len=4;
        if(transfer(fd,messages,2)) goto done;
        printf("%s stock_four_bytes=%02x%02x%02x%02x\n",states[i].name,short_read[0],short_read[1],short_read[2],short_read[3]);
        messages[1].buf=block;messages[1].len=36;
        if(transfer(fd,messages,2)) goto done;
        printf("%s command=0x%04x request=3e%02x%02x response=",states[i].name,states[i].command,request[1],request[2]);
        for(j=0;j<36;j++)printf("%02x",block[j]);
        printf(" validation=%d\n",validate(&states[i],block));fflush(stdout);
        if(validate(&states[i],block) || memcmp(short_read,block,4)) goto done;
    }
    rc=0;
done:
    if(rc)fprintf(stderr,"Stop on transfer/identity/firmware/echo/length/checksum mismatch; no retry\n");
    close(fd);close(lock);return rc;
}
