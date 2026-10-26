/* Fixed stock bq28z610_get_2cell_voltage() protocol, address 0x55.
 * Realme 9668fcdc gauge source: 3E 71 00, wait >=1ms, read 4 bytes at 40.
 * Require the same client's legacy DeviceType 0xFFA5 first. Observe the
 * extended response too, but never use undocumented status/control opcodes.
 * No charging settings, protection/FET switches, calibration or NVM writes.
 */
#define main status_reader_main
#include "read-bq28-status.c"
#undef main

static int transfer(int fd, struct i2c_msg *messages, unsigned int count)
{
    struct i2c_rdwr_ioctl_data t = {.msgs=messages,.nmsgs=count};
    if (ioctl(fd,I2C_RDWR,&t)!=(int)count) { perror("fixed stock transaction"); return 1; }
    return 0;
}

int main(int argc, char **argv)
{
    uint8_t devreq[3]={0x00,0x01,0x00}, request[3]={0x3e,0x71,0x00};
    uint8_t selector=0x00, legacy[2], cells[4], block[36], pack[2];
    struct i2c_msg write={.addr=0x55,.len=3,.buf=devreq};
    struct i2c_msg messages[2]={
        {.addr=0x55,.len=1,.buf=&selector},
        {.addr=0x55,.flags=I2C_M_RD,.len=2,.buf=legacy},
    };
    const struct query da={0x0071,32,"DAStatus1"};
    unsigned long functions;
    unsigned int i, c1, c2, voltage;
    int fd, lock, rc=1;
    if (argc!=2 || !guard(argv[1])) { fprintf(stderr,"Refusing adapter/client/driver mismatch\n"); return 2; }
    lock=open("/tmp/bq28-status-observation.lock",O_CREAT|O_RDWR|O_CLOEXEC|O_NOFOLLOW,0600);
    if(lock<0 || flock(lock,LOCK_EX|LOCK_NB)) { perror("single observer"); if(lock>=0)close(lock);return 1; }
    fd=open(argv[1],O_RDONLY|O_CLOEXEC);
    if(fd<0) { perror("adapter");close(lock);return 1; }
    if(ioctl(fd,I2C_FUNCS,&functions)<0 || !(functions&I2C_FUNC_I2C)) goto done;
    if(transfer(fd,&write,1) || usleep(1000) || transfer(fd,messages,2)) goto done;
    printf("DeviceType request=000100 legacy_word=0x%04x\n",(unsigned int)legacy[0]|((unsigned int)legacy[1]<<8));
    if(legacy[0]!=0xa5 || legacy[1]!=0xff) { fprintf(stderr,"Legacy identity mismatch; no cell query\n");goto done; }
    write.buf=request;
    if(transfer(fd,&write,1) || usleep(1000)) goto done;
    selector=0x40; messages[1].buf=cells; messages[1].len=4;
    if(transfer(fd,messages,2)) goto done;
    c1=(unsigned int)cells[0]|((unsigned int)cells[1]<<8);
    c2=(unsigned int)cells[2]|((unsigned int)cells[3]<<8);
    printf("stock_cells request=3e7100 read_register=0x40 data=%02x%02x%02x%02x cell1_mV=%u cell2_mV=%u\n",cells[0],cells[1],cells[2],cells[3],c1,c2);
    selector=0x3e; messages[1].buf=block; messages[1].len=36;
    if(transfer(fd,messages,2)) goto done;
    printf("DAStatus1 extended_response=");
    for(i=0;i<36;i++)printf("%02x",block[i]);
    printf(" validation=%d\n",validate(&da,block));
    if(validate(&da,block) || memcmp(cells,block+2,4)) { fprintf(stderr,"Extended cell response mismatch; no retry\n");goto done; }
    selector=0x08; messages[1].buf=pack; messages[1].len=2;
    if(transfer(fd,messages,2)) goto done;
    voltage=(unsigned int)pack[0]|((unsigned int)pack[1]<<8);
    printf("standard_pack_mV=%u cell_sum_mV=%u; readings_are_not_protection_thresholds\n",voltage,c1+c2);
    rc=0;
done:
    close(fd);close(lock);return rc;
}
