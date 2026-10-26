/* SPDX-License-Identifier: MIT */
/* Bounded native DSI timing comparison; no kernel/partition/DSC changes. */
#include <drm/drm.h>
#include <drm/drm_mode.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <time.h>
#include <unistd.h>

static volatile sig_atomic_t interrupted;
static void stop(int signum) { (void)signum; interrupted=1; }
static uint64_t pointer(void *p) { return (uint64_t)(uintptr_t)p; }
static double seconds(void)
{
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC,&t)) return -1;
    return (double)t.tv_sec+(double)t.tv_nsec/1e9;
}
static int output_state(const char *label)
{
    static const char *paths[]={"/sys/kernel/debug/clk/clk_summary",
        "/sys/kernel/debug/dri/1/encoder-0/status","/sys/kernel/debug/dri/1/state"};
    char name[256],buffer[4096];
    for (unsigned i=0;i<sizeof(paths)/sizeof(paths[0]);i++) {
        snprintf(name,sizeof(name),"%s-state-%u.txt",label,i);
        int src=open(paths[i],O_RDONLY|O_CLOEXEC), dst=open(name,O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC,0600);
        if (src<0 || dst<0) { if(src>=0)close(src);if(dst>=0)close(dst);return -1; }
        ssize_t n;
        while ((n=read(src,buffer,sizeof(buffer)))>0) {
            ssize_t at=0;
            while (at<n) { ssize_t k=write(dst,buffer+at,(size_t)(n-at));if(k<=0){close(src);close(dst);return -1;}at+=k; }
        }
        close(src);close(dst);
        if(n<0)return -1;
    }
    return 0;
}
int main(void)
{
    signal(SIGTERM,stop);signal(SIGINT,stop);
    int fd=-1,result=1,submitted=0;
    uint32_t ids[32]={0},crtcs[8]={0},selected=0,encoder_ids[32]={0};
    struct drm_mode_modeinfo modes[32]={0},base={0};
    struct drm_mode_create_dumb dumb[2]={{0}};
    struct drm_mode_fb_cmd fb[2]={{0}};
    uint32_t *pixels[2]={MAP_FAILED,MAP_FAILED};
    char name[32]={0};
    struct drm_version ver={.name=name,.name_len=sizeof(name)-1};
    struct drm_mode_card_res res={0};
    struct drm_mode_get_connector conn={0};
    struct drm_mode_crtc original={0},off={0};
#define CHECK(expr,what) do { if(!(expr)){perror(what);goto done;} }while(0)
    fd=open("/dev/dri/card1",O_RDWR|O_CLOEXEC);
    CHECK(fd>=0,"open DRM");
    CHECK(!ioctl(fd,DRM_IOCTL_VERSION,&ver)&&!strcmp(name,"msm"),"require native msm");
    CHECK(!ioctl(fd,DRM_IOCTL_SET_MASTER,0),"DRM master (greetd must be stopped)");
    CHECK(!ioctl(fd,DRM_IOCTL_MODE_GETRESOURCES,&res),"resources");
    CHECK(res.count_connectors>0&&res.count_connectors<=32&&res.count_crtcs>0&&res.count_crtcs<=8,"resource bounds");
    res.connector_id_ptr=pointer(ids);res.crtc_id_ptr=pointer(crtcs);res.count_encoders=0;res.count_fbs=0;
    CHECK(!ioctl(fd,DRM_IOCTL_MODE_GETRESOURCES,&res),"resource IDs");
    for(unsigned i=0;i<res.count_connectors;i++) {
        struct drm_mode_get_connector probe={.connector_id=ids[i]};
        CHECK(!ioctl(fd,DRM_IOCTL_MODE_GETCONNECTOR,&probe),"connector");
        if(probe.connection==1&&probe.connector_type==DRM_MODE_CONNECTOR_DSI) {
            CHECK(!selected,"unique connected DSI");selected=ids[i];conn=probe;
        }
    }
    CHECK(selected&&conn.count_modes>0&&conn.count_modes<=32&&conn.count_encoders>0&&conn.count_encoders<=32,"DSI bounds");
    conn.modes_ptr=pointer(modes);conn.encoders_ptr=pointer(encoder_ids);conn.count_props=0;
    CHECK(!ioctl(fd,DRM_IOCTL_MODE_GETCONNECTOR,&conn),"DSI modes");
    unsigned matched=0;
    for(unsigned i=0;i<conn.count_modes;i++)if(modes[i].hdisplay==1080&&modes[i].vdisplay==2400) {base=modes[i];matched++;}
    CHECK(matched==1&&base.htotal==1144&&base.vtotal==2428&&base.clock==166657,"original 60 Hz mode");
    struct drm_mode_get_encoder enc={.encoder_id=encoder_ids[0]};
    CHECK(!ioctl(fd,DRM_IOCTL_MODE_GETENCODER,&enc),"encoder");
    for(unsigned i=0;i<res.count_crtcs;i++)if(enc.possible_crtcs&(1u<<i)){original.crtc_id=crtcs[i];break;}
    CHECK(original.crtc_id&&!ioctl(fd,DRM_IOCTL_MODE_GETCRTC,&original),"CRTC");
    CHECK(!original.mode_valid&&!original.fb_id,"CRTC must be inactive after GUI stop");
    off.crtc_id=original.crtc_id;
    for(unsigned k=0;k<2;k++) {
        dumb[k].width=1080;dumb[k].height=2400;dumb[k].bpp=32;
        CHECK(!ioctl(fd,DRM_IOCTL_MODE_CREATE_DUMB,&dumb[k]),"dumb buffer");
        struct drm_mode_map_dumb map={.handle=dumb[k].handle};
        CHECK(!ioctl(fd,DRM_IOCTL_MODE_MAP_DUMB,&map),"map dumb offset");
        pixels[k]=mmap(NULL,dumb[k].size,PROT_READ|PROT_WRITE,MAP_SHARED,fd,map.offset);
        CHECK(pixels[k]!=MAP_FAILED,"mmap");
        for(unsigned y=0;y<2400;y++)for(unsigned x=0;x<1080;x++) {
            uint32_t color=((x/120+y/120)&1)?0x606060:0x303030;
            if(y>=100&&y<130&&x>=100+k*80&&x<160+k*80)color=0x90c090;
            pixels[k][y*(dumb[k].pitch/4)+x]=color;
        }
        fb[k]=(struct drm_mode_fb_cmd){.width=1080,.height=2400,.pitch=dumb[k].pitch,.bpp=32,.depth=24,.handle=dumb[k].handle};
        CHECK(!ioctl(fd,DRM_IOCTL_MODE_ADDFB,&fb[k]),"add FB");
    }
    for(unsigned phase=0;phase<3&&!interrupted;phase++) {
        struct drm_mode_modeinfo mode=base;
        const char *label=phase==0?"baseline":phase==1?"stock-rate":"return-baseline";
        if(phase==1) {
            /* CMD porches represent transfer overhead; retain refresh and PPS. */
            mode.hsync_start=1080+874;mode.hsync_end=mode.hsync_start+16;mode.htotal=mode.hsync_end+16;
            mode.clock=(uint32_t)((uint64_t)mode.htotal*mode.vtotal*60/1000);
            mode.type=DRM_MODE_TYPE_USERDEF;mode.vrefresh=60;
            snprintf(mode.name,sizeof(mode.name),"1080x2400-clock-probe");
        }
        struct drm_mode_crtc crtc={.crtc_id=original.crtc_id,.fb_id=fb[0].fb_id,.mode_valid=1,
            .mode=mode,.set_connectors_ptr=pointer(&selected),.count_connectors=1};
        printf("PHASE_BEGIN name=%s clock_khz=%u htotal=%u vtotal=%u refresh=60\n",label,mode.clock,mode.htotal,mode.vtotal);fflush(stdout);
        submitted=1;
        CHECK(!ioctl(fd,DRM_IOCTL_MODE_SETCRTC,&crtc),"set phase mode");
        CHECK(!output_state(label),"phase clock/DRM state");
        double start=seconds();unsigned flips=0;
        CHECK(start>=0,"monotonic time");
        while(!interrupted&&seconds()-start<20.0) {
            struct drm_mode_crtc_page_flip flip={.crtc_id=original.crtc_id,.fb_id=fb[(flips+1)&1].fb_id,
                .flags=DRM_MODE_PAGE_FLIP_EVENT,.user_data=flips+1};
            CHECK(!ioctl(fd,DRM_IOCTL_MODE_PAGE_FLIP,&flip),"page flip");
            struct pollfd p={.fd=fd,.events=POLLIN};int ready;
            do {ready=poll(&p,1,1500);}while(ready<0&&errno==EINTR&&!interrupted);
            if(interrupted)break;
            CHECK(ready>0&&(p.revents&POLLIN),"page flip timeout");
            struct drm_event_vblank event;
            CHECK(read(fd,&event,sizeof(event))==(ssize_t)sizeof(event)&&event.base.length==sizeof(event)&&
                  event.base.type==DRM_EVENT_FLIP_COMPLETE&&event.user_data==flips+1,"page flip event");
            flips++;
            /* Short periods exercise active rendering; long pauses exercise idle PC. */
            struct timespec delay={.tv_sec=flips%10==0?1:0,.tv_nsec=flips%10==0?0:50000000};
            while(nanosleep(&delay,&delay)<0&&errno==EINTR&&!interrupted){}
        }
        printf("PHASE_END name=%s flips=%u elapsed=%.6f interrupted=%d\n",label,flips,seconds()-start,interrupted);fflush(stdout);
        CHECK(!ioctl(fd,DRM_IOCTL_MODE_SETCRTC,&off),"disable phase");submitted=0;
        struct timespec delay={.tv_sec=1};while(nanosleep(&delay,&delay)<0&&errno==EINTR&&!interrupted){}
    }
    result=interrupted?2:0;
done:
    if(fd>=0) {
        if(submitted&&ioctl(fd,DRM_IOCTL_MODE_SETCRTC,&off)){perror("cleanup CRTC disable");result=1;}
        for(unsigned k=0;k<2;k++) {
            if(fb[k].fb_id&&ioctl(fd,DRM_IOCTL_MODE_RMFB,&fb[k].fb_id)){perror("cleanup FB");result=1;}
            if(pixels[k]!=MAP_FAILED)munmap(pixels[k],dumb[k].size);
            if(dumb[k].handle){struct drm_mode_destroy_dumb destroy={.handle=dumb[k].handle};if(ioctl(fd,DRM_IOCTL_MODE_DESTROY_DUMB,&destroy)){perror("cleanup dumb");result=1;}}
        }
        ioctl(fd,DRM_IOCTL_DROP_MASTER,0);close(fd);
    }
    printf("PROBE_EXIT result=%d\n",result);
    return result;
}
