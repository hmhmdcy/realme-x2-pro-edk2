// SPDX-License-Identifier: GPL-2.0-only
/* Short, low-strength FF_RUMBLE test. Always stops/erases before closing. */
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <fcntl.h>
#include <linux/input.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <time.h>
#include <unistd.h>

static volatile sig_atomic_t interrupted;
static void stop_signal(int number) { (void)number; interrupted = 1; }
static int event(int fd, int id, int value)
{
    struct input_event e = {.type=EV_FF, .code=(unsigned short)id, .value=value};
    ssize_t n;
    do { n=write(fd,&e,sizeof(e)); } while (n<0 && errno==EINTR);
    return n==(ssize_t)sizeof(e) ? 0 : -1;
}
static int integer(const char *text, unsigned int low, unsigned int high, unsigned int *value)
{
    char *end;
    unsigned long n;
    errno=0; n=strtoul(text,&end,10);
    if(errno || end==text || *end || n<low || n>high) return -1;
    *value=(unsigned int)n; return 0;
}
int main(int argc, char **argv)
{
    unsigned int percent, duration;
    int fd=-1, result=1, uploaded=0;
    struct ff_effect effect={.type=FF_RUMBLE,.id=-1};
    struct sigaction action={.sa_handler=stop_signal};
    char name[128]={0};
    unsigned long capabilities[(FF_MAX+8*sizeof(unsigned long))/(8*sizeof(unsigned long))]={0};
    struct timespec interval={.tv_sec=0,.tv_nsec=10000000L};
    if(argc!=4 || integer(argv[2],1,35,&percent) || integer(argv[3],10,500,&duration)) {
        fputs("Usage: ff-pulse /dev/input/eventN percent(1..35) milliseconds(10..500)\n",stderr);
        return 2;
    }
    sigemptyset(&action.sa_mask);
    sigaction(SIGINT,&action,NULL); sigaction(SIGTERM,&action,NULL);
    fd=open(argv[1],O_RDWR|O_CLOEXEC);
    if(fd<0) {perror("open");goto done;}
    if(ioctl(fd,EVIOCGNAME(sizeof(name)),name)<0 || strcmp(name,"Realme X2 Pro AW8697 haptics")) {
        fputs("Unexpected input device\n",stderr);goto done;
    }
    if(ioctl(fd,EVIOCGBIT(EV_FF,sizeof(capabilities)),capabilities)<0 ||
       !(capabilities[FF_RUMBLE/(8*sizeof(unsigned long))] & (1UL<<(FF_RUMBLE%(8*sizeof(unsigned long)))))) {
        fputs("FF_RUMBLE unavailable\n",stderr);goto done;
    }
    effect.replay.length=(unsigned short)duration;
    effect.u.rumble.strong_magnitude=(unsigned short)(percent*65535U/100U);
    if(ioctl(fd,EVIOCSFF,&effect)<0) {perror("EVIOCSFF");goto done;}
    uploaded=1;
    puts("FF_UPLOAD_PASS");fflush(stdout);
    if(interrupted || event(fd,effect.id,1)) {perror("start");goto done;}
    puts("FF_START_PASS");fflush(stdout);
    for(unsigned int elapsed=0;elapsed<duration+50 && !interrupted;elapsed+=10)
        nanosleep(&interval,NULL);
    if(event(fd,effect.id,0)) {perror("stop");goto done;}
    puts("FF_STOP_PASS");fflush(stdout);
    result=interrupted ? 130 : 0;
done:
    if(uploaded) {
        if(event(fd,effect.id,0)) result=1;
        if(ioctl(fd,EVIOCRMFF,effect.id)<0) {perror("EVIOCRMFF");result=1;}
        else puts("FF_ERASE_PASS");
    }
    if(fd>=0) close(fd);
    return result;
}
