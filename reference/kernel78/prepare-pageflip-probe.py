from pathlib import Path

ref = Path(__file__).resolve().parent
src = (ref / 'kms-refresh.c').read_text()
src = src.replace('    struct drm_mode_crtc old = {0}, crtc = {0};', '''    struct drm_mode_crtc old = {0}, crtc = {0};
    struct drm_mode_create_dumb dumb2 = {0};
    struct drm_mode_map_dumb map2 = {0};
    struct drm_mode_fb_cmd fb2 = {0};
    uint32_t *pixels2;''')
src = src.replace('    crtc.crtc_id=old.crtc_id;', '''    dumb2.width=dumb.width;dumb2.height=dumb.height;dumb2.bpp=32;
    if (ioctl(fd, DRM_IOCTL_MODE_CREATE_DUMB,&dumb2)) fail("create white buffer");
    map2.handle=dumb2.handle;
    if (ioctl(fd, DRM_IOCTL_MODE_MAP_DUMB,&map2)) fail("map white buffer offset");
    pixels2=mmap(NULL,dumb2.size,PROT_READ|PROT_WRITE,MAP_SHARED,fd,map2.offset);
    if (pixels2==MAP_FAILED) fail("mmap white buffer");
    for(y=0;y<dumb2.height;y++) for(x=0;x<dumb2.width;x++)
        pixels2[y*(dumb2.pitch/4)+x]=0xffffff;
    fb2.width=dumb2.width;fb2.height=dumb2.height;fb2.pitch=dumb2.pitch;
    fb2.bpp=32;fb2.depth=24;fb2.handle=dumb2.handle;
    if (ioctl(fd,DRM_IOCTL_MODE_ADDFB,&fb2)) fail("add white framebuffer");
    crtc.crtc_id=old.crtc_id;''')
src = src.replace('''        pattern = (i / 60) & 1;
        for (y=0;y<dumb.height;y++) for(x=0;x<dumb.width;x++)
            pixels[y*(dumb.pitch/4)+x]=pattern ? 0xffffff : colors[(x*8)/dumb.width];
        struct drm_mode_fb_dirty_cmd dirty={.fb_id=fb.fb_id};
        if(ioctl(fd,DRM_IOCTL_MODE_DIRTYFB,&dirty)) fail("refresh command mode framebuffer");
        struct pollfd p={.fd=crcfd,.events=POLLIN};
        if(poll(&p,1,2000)<=0) fail("CRC timeout");
        ssize_t n=read(crcfd,data,sizeof(data)-1);
        if(n<0) fail("CRC read");
        data[n]=0;
        printf("sample=%u pattern=%u scanout CRC %s",i,pattern,data);''', '''        pattern = i & 1;
        struct drm_mode_crtc_page_flip flip={
            .crtc_id=old.crtc_id,.fb_id=pattern ? fb2.fb_id : fb.fb_id,
            .flags=DRM_MODE_PAGE_FLIP_EVENT,.user_data=i+1,
        };
        if(ioctl(fd,DRM_IOCTL_MODE_PAGE_FLIP,&flip)) fail("page flip");
        struct pollfd eventpoll={.fd=fd,.events=POLLIN};
        if(poll(&eventpoll,1,2000)<=0) fail("page flip event timeout");
        struct drm_event_vblank event;
        ssize_t eventbytes=read(fd,&event,sizeof(event));
        if(eventbytes!=sizeof(event) || event.base.type!=DRM_EVENT_FLIP_COMPLETE || event.user_data!=i+1)
            fail("page flip event mismatch");
        uint32_t first=0,second=0,crcseq=0;
        unsigned trial;
        for(trial=0;trial<16;trial++) {
            struct pollfd p={.fd=crcfd,.events=POLLIN};
            if(poll(&p,1,2000)<=0) fail("CRC timeout");
            ssize_t n=read(crcfd,data,sizeof(data)-1);
            if(n<0) fail("CRC read");
            data[n]=0;
            if(sscanf(data,"%x %x %x",&crcseq,&first,&second)!=3) fail("CRC parse");
            printf("sample=%u pattern=%u event=%u scanout CRC %s",i,pattern,event.sequence,data);
            if(pattern ? (first==0x25e11871 && second==0x25e11871) :
                         (first==0x69961448 && second==0x60af15f5)) break;
            if(!((first==0x25e11871 && second==0x25e11871) ||
                 (first==0x69961448 && second==0x60af15f5))) fail("unexpected stable-buffer CRC");
        }
        if(trial==16) fail("requested pattern CRC missing");''')
src = src.replace('600 redraws elapsed=', '600 page flips elapsed=')
src = src.replace('    munmap(pixels,dumb.size);', '''    if (ioctl(fd,DRM_IOCTL_MODE_RMFB,&fb2.fb_id)) fail("remove white framebuffer");
    munmap(pixels2,dumb2.size);
    struct drm_mode_destroy_dumb destroy2={.handle=dumb2.handle};
    if (ioctl(fd,DRM_IOCTL_MODE_DESTROY_DUMB,&destroy2)) fail("destroy white buffer");
    munmap(pixels,dumb.size);''')
assert 'DRM_IOCTL_MODE_PAGE_FLIP' in src
assert 'DRM_IOCTL_MODE_DIRTYFB' not in src
assert 'DRM_IOCTL_MODE_SETCRTC,&off' not in src
(ref / 'kms-pageflip.c').write_text(src)
print('Prepared two immutable framebuffers and event-checked page flips')
