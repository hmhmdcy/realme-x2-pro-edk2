// SPDX-License-Identifier: GPL-2.0-only
/* Fixed low-strength, supervised lifecycle tests for this input device. */
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <fcntl.h>
#include <linux/input.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <time.h>
#include <unistd.h>

static int send_event(int fd, int id, int value)
{
    struct input_event e={.type=EV_FF,.code=(unsigned short)id,.value=value};
    ssize_t n;
    do { n=write(fd,&e,sizeof(e)); } while(n<0 && errno==EINTR);
    return n==(ssize_t)sizeof(e) ? 0 : -1;
}
int main(int argc, char **argv)
{
    char name[128]={0};
    int fd, result=1;
    struct ff_effect effect={.type=FF_RUMBLE,.id=-1};
    struct timespec interval={.tv_sec=0,.tv_nsec=10000000L};
    unsigned milliseconds;
    if(argc!=3 || (strcmp(argv[2],"close") && strcmp(argv[2],"kill") && strcmp(argv[2],"watchdog"))) return 2;
    milliseconds=!strcmp(argv[2],"close") ? 120 : 1800;
    fd=open(argv[1],O_RDWR|O_CLOEXEC);
    if(fd<0) {perror("open");return 1;}
    if(ioctl(fd,EVIOCGNAME(sizeof(name)),name)<0 || strcmp(name,"Realme X2 Pro AW8697 haptics")) goto done;
    effect.replay.length=1500;
    effect.u.rumble.strong_magnitude=6553; /* 10%, hardware watchdog at 1 s. */
    if(ioctl(fd,EVIOCSFF,&effect)<0 || send_event(fd,effect.id,1)) {perror("FF start");goto done;}
    puts("FF_LIFECYCLE_STARTED");fflush(stdout);
    for(unsigned elapsed=0;elapsed<milliseconds;elapsed+=10) nanosleep(&interval,NULL);
    /* close/kill intentionally omit stop/erase, to verify evdev cleanup. */
    if(!strcmp(argv[2],"watchdog")) {
        puts("WATCHDOG_FD_STILL_OPEN_AFTER_1800MS");fflush(stdout);
        if(send_event(fd,effect.id,0) || ioctl(fd,EVIOCRMFF,effect.id)<0) goto done;
    }
    result=0;
done:
    close(fd);
    if(!result) puts("FF_LIFECYCLE_CLOSED");
    return result;
}
