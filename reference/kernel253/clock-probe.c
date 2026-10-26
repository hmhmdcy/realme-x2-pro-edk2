/* Read-only realtime/boot/monotonic observation; no clock changes. */
#define _GNU_SOURCE
#include <stdio.h>
#include <time.h>
#include <stdint.h>
#include <inttypes.h>
int main(void){
 struct timespec a,b,c;
 if(clock_gettime(CLOCK_REALTIME,&a)||clock_gettime(CLOCK_BOOTTIME,&b)||clock_gettime(CLOCK_MONOTONIC,&c))return 1;
 printf("{\"realtime_ms\":%"PRIu64",\"boottime_ms\":%"PRIu64",\"monotonic_ms\":%"PRIu64"}\n",(uint64_t)a.tv_sec*1000+a.tv_nsec/1000000,(uint64_t)b.tv_sec*1000+b.tv_nsec/1000000,(uint64_t)c.tv_sec*1000+c.tv_nsec/1000000);
 return 0;
}
