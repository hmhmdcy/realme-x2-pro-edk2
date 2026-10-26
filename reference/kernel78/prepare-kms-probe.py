from pathlib import Path

ref = Path(__file__).resolve().parent
src = (ref.parent / 'kernel73/kms-smoke.c').read_text()
src = src.replace('for(i=0;i<8;i++) {', '''double refresh_start=now();
    for(i=0;i<600;i++) {
        pattern = (i / 60) & 1;
        for (y=0;y<dumb.height;y++) for(x=0;x<dumb.width;x++)
            pixels[y*(dumb.pitch/4)+x]=pattern ? 0xffffff : colors[(x*8)/dumb.width];''')
src = src.replace('printf("pattern=%u scanout CRC %s",pattern,data);',
                  'printf("sample=%u pattern=%u scanout CRC %s",i,pattern,data);')
src = src.replace('    close(crcfd);', '    printf("600 redraws elapsed=%.6f seconds\\n",now()-refresh_start);\n    close(crcfd);')
src = src.replace('    struct drm_mode_crtc off={.crtc_id=old.crtc_id};\n'
                  '    if(ioctl(fd,DRM_IOCTL_MODE_SETCRTC,&off)) fail("disable native CRTC");\n'
                  '    usleep(200000);\n', '')
src = src.replace('Native panel disable/unprepare and prepare/enable cycle passed',
                  'No panel power cycle requested; original CRTC restored directly')
(ref / 'kms-refresh.c').write_text(src)
print('Prepared continuous redraw probe without CRTC disable or panel power cycle')
