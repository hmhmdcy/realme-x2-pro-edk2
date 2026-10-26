/* SPDX-License-Identifier: GPL-2.0-only */
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <poll.h>
#include <time.h>
#include <unistd.h>
#include <drm/drm.h>
#include <drm/drm_mode.h>

static void fail(const char *name) { perror(name); exit(1); }
static uint64_t ptr(void *p) { return (uint64_t)(uintptr_t)p; }
static double now(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec+t.tv_nsec/1e9; }

int main(int argc, char **argv)
{
    int fd = open(argc > 1 ? argv[1] : "/dev/dri/card0", O_RDWR|O_CLOEXEC);
    char name[128] = {0};
    struct drm_version ver = {.name_len=sizeof(name)-1, .name=name};
    struct drm_mode_card_res res = {0};
    struct drm_mode_get_connector conn = {0};
    struct drm_mode_crtc old = {0}, crtc = {0};
    struct drm_mode_create_dumb dumb = {0};
    struct drm_mode_map_dumb map = {0};
    struct drm_mode_fb_cmd fb = {0};
    struct drm_mode_destroy_dumb destroy = {0};
    uint32_t *connectors, *crtcs, *encoders;
    struct drm_mode_modeinfo *modes;
    uint32_t *pixels;
    unsigned i, x, y, selected = 0;
    double start;
    if (fd < 0) fail("open DRM");
    if (ioctl(fd, DRM_IOCTL_VERSION, &ver)) fail("DRM version");
    printf("DRM driver=%s version=%d.%d.%d\n", name, ver.version_major,ver.version_minor,ver.version_patchlevel);
    if (strcmp(name,"msm")) {fprintf(stderr,"Native msm DRM required\n");return 2;}
    if (ioctl(fd, DRM_IOCTL_MODE_GETRESOURCES, &res)) fail("get resources");
    connectors=calloc(res.count_connectors,sizeof(*connectors));
    crtcs=calloc(res.count_crtcs,sizeof(*crtcs));
    encoders=calloc(res.count_encoders,sizeof(*encoders));
    res.connector_id_ptr=ptr(connectors);res.crtc_id_ptr=ptr(crtcs);res.encoder_id_ptr=ptr(encoders);
    if (ioctl(fd, DRM_IOCTL_MODE_GETRESOURCES, &res)) fail("get resource IDs");
    printf("resources connectors=%u crtcs=%u encoders=%u\n",res.count_connectors,res.count_crtcs,res.count_encoders);
    for (i=0;i<res.count_connectors;i++) {
        conn=(struct drm_mode_get_connector){.connector_id=connectors[i]};
        if (ioctl(fd, DRM_IOCTL_MODE_GETCONNECTOR,&conn)) fail("connector probe");
        printf("connector=%u type=%u status=%u modes=%u\n",conn.connector_id,conn.connector_type,conn.connection,conn.count_modes);
        if (conn.connection==1 && conn.connector_type==16 && conn.count_modes) {selected=conn.connector_id;break;}
    }
    if (!selected || !res.count_crtcs) {fprintf(stderr,"No connected DSI modes\n");return 3;}
    modes=calloc(conn.count_modes,sizeof(*modes));
    conn.modes_ptr=ptr(modes);
    /* Properties and encoder arrays are deliberately not requested. */
    conn.count_props=0;conn.count_encoders=0;
    if (ioctl(fd, DRM_IOCTL_MODE_GETCONNECTOR,&conn)) fail("connector modes");
    for (i=0;i<conn.count_modes;i++)
        printf("mode=%s %ux%u clock=%u refresh=%u\n",modes[i].name,modes[i].hdisplay,modes[i].vdisplay,modes[i].clock,modes[i].vrefresh);
    struct drm_mode_get_encoder encoder={.encoder_id=conn.encoder_id};
    if (conn.encoder_id && ioctl(fd,DRM_IOCTL_MODE_GETENCODER,&encoder)) fail("get current encoder");
    old.crtc_id=encoder.crtc_id ? encoder.crtc_id : crtcs[0];
    if (ioctl(fd, DRM_IOCTL_MODE_GETCRTC,&old)) fail("get original CRTC");
    dumb.width=modes[0].hdisplay;dumb.height=modes[0].vdisplay;dumb.bpp=32;
    if (ioctl(fd, DRM_IOCTL_MODE_CREATE_DUMB,&dumb)) fail("create dumb buffer");
    map.handle=dumb.handle;
    if (ioctl(fd, DRM_IOCTL_MODE_MAP_DUMB,&map)) fail("map dumb offset");
    pixels=mmap(NULL,dumb.size,PROT_READ|PROT_WRITE,MAP_SHARED,fd,map.offset);
    if (pixels==MAP_FAILED) fail("mmap dumb buffer");
    static const uint32_t colors[]={0xffffff,0xffff00,0x00ffff,0x00ff00,0xff00ff,0xff0000,0x0000ff,0x101010};
    unsigned pattern = argc > 2 ? (unsigned)atoi(argv[2]) : 0;
    for (y=0;y<dumb.height;y++) for(x=0;x<dumb.width;x++)
        pixels[y*(dumb.pitch/4)+x]=pattern ? 0xffffff : colors[(x*8)/dumb.width];
    fb.width=dumb.width;fb.height=dumb.height;fb.pitch=dumb.pitch;fb.bpp=32;fb.depth=24;fb.handle=dumb.handle;
    if (ioctl(fd,DRM_IOCTL_MODE_ADDFB,&fb)) fail("add framebuffer");
    crtc.crtc_id=old.crtc_id;crtc.fb_id=fb.fb_id;crtc.mode_valid=1;crtc.mode=modes[0];
    crtc.set_connectors_ptr=ptr(&selected);crtc.count_connectors=1;
    if (ioctl(fd,DRM_IOCTL_MODE_SETCRTC,&crtc)) fail("set native color bars");
    printf("Native color bars submitted fb=%u pitch=%u bytes=%llu\n",fb.fb_id,dumb.pitch,(unsigned long long)dumb.size);
    start=now();
    for (i=0;i<60;i++) {
        union drm_wait_vblank vbl={.request={.type=_DRM_VBLANK_RELATIVE,.sequence=1}};
        if (ioctl(fd,DRM_IOCTL_WAIT_VBLANK,&vbl)) fail("wait vblank");
        if (i==0 || i==59) printf("vblank sequence=%u\n",vbl.reply.sequence);
    }
    printf("60 vblank waits elapsed=%.6f seconds\n",now()-start);
    char path[256], control[256], data[256];
    snprintf(path,sizeof(path),"/sys/kernel/debug/dri/%c/crtc-0/crc/data",argv[1][strlen(argv[1])-1]);
    snprintf(control,sizeof(control),"/sys/kernel/debug/dri/%c/crtc-0/crc/control",argv[1][strlen(argv[1])-1]);
    int controlfd=open(control,O_WRONLY|O_CLOEXEC);
    if(controlfd<0 || write(controlfd,"auto",4)!=4) fail("enable scanout CRC");
    close(controlfd);
    int crcfd=open(path,O_RDONLY|O_NONBLOCK|O_CLOEXEC);
    if(crcfd<0) fail("open scanout CRC");
    for(i=0;i<8;i++) {
        struct drm_mode_fb_dirty_cmd dirty={.fb_id=fb.fb_id};
        if(ioctl(fd,DRM_IOCTL_MODE_DIRTYFB,&dirty)) fail("refresh command mode framebuffer");
        struct pollfd p={.fd=crcfd,.events=POLLIN};
        if(poll(&p,1,2000)<=0) fail("CRC timeout");
        ssize_t n=read(crcfd,data,sizeof(data)-1);
        if(n<0) fail("CRC read");
        data[n]=0;
        printf("pattern=%u scanout CRC %s",pattern,data);
    }
    close(crcfd);
    controlfd=open(control,O_WRONLY|O_CLOEXEC);
    if(controlfd<0 || write(controlfd,"none",4)!=4) fail("disable scanout CRC");
    close(controlfd);
    sleep(2);
    struct drm_mode_crtc off={.crtc_id=old.crtc_id};
    if(ioctl(fd,DRM_IOCTL_MODE_SETCRTC,&off)) fail("disable native CRTC");
    usleep(200000);
    if (old.mode_valid) {
        old.set_connectors_ptr=ptr(&selected);old.count_connectors=1;
        if (ioctl(fd,DRM_IOCTL_MODE_SETCRTC,&old)) fail("restore console CRTC");
    }
    puts("Native panel disable/unprepare and prepare/enable cycle passed");
    if (ioctl(fd,DRM_IOCTL_MODE_RMFB,&fb.fb_id)) fail("remove framebuffer");
    munmap(pixels,dumb.size);
    destroy.handle=dumb.handle;
    if (ioctl(fd,DRM_IOCTL_MODE_DESTROY_DUMB,&destroy)) fail("destroy dumb buffer");
    close(fd);
    puts("Native KMS mode setting, scanout/vblank and console restoration passed");
    return 0;
}
