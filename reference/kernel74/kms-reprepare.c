/* SPDX-License-Identifier: GPL-2.0-only */
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <drm/drm.h>
#include <drm/drm_mode.h>

int main(void)
{
    int fd = open("/dev/dri/card1", O_RDWR | O_CLOEXEC);
    uint32_t connectors[8], crtcs[8];
    struct drm_mode_card_res res = {
        .connector_id_ptr = (uintptr_t)connectors, .count_connectors = 8,
        .crtc_id_ptr = (uintptr_t)crtcs, .count_crtcs = 8,
    };
    struct drm_mode_get_connector conn = {0};
    struct drm_mode_get_encoder enc = {0};
    struct drm_mode_crtc old = {0}, off = {0};
    if (fd < 0 || ioctl(fd, DRM_IOCTL_MODE_GETRESOURCES, &res)) goto fail;
    if (!res.count_connectors || res.count_connectors > 8) return 2;
    conn.connector_id = connectors[0];
    if (ioctl(fd, DRM_IOCTL_MODE_GETCONNECTOR, &conn)) goto fail;
    enc.encoder_id = conn.encoder_id;
    if (ioctl(fd, DRM_IOCTL_MODE_GETENCODER, &enc)) goto fail;
    old.crtc_id = enc.crtc_id;
    if (ioctl(fd, DRM_IOCTL_MODE_GETCRTC, &old)) goto fail;
    if (!old.mode_valid) return 3;
    off.crtc_id = old.crtc_id;
    if (ioctl(fd, DRM_IOCTL_MODE_SETCRTC, &off)) goto fail;
    sleep(1);
    old.set_connectors_ptr = (uintptr_t)&conn.connector_id;
    old.count_connectors = 1;
    if (ioctl(fd, DRM_IOCTL_MODE_SETCRTC, &old)) goto fail;
    close(fd);
    puts("Diagnostic full disable/unprepare and prepare/enable requested");
    return 0;
fail:
    perror("DRM reprepare");
    if (fd >= 0) close(fd);
    return 1;
}
