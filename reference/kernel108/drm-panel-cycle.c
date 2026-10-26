/* SPDX-License-Identifier: MIT */
/* Cycle the active native DSI CRTC once and restore its original framebuffer. */
#include <drm/drm.h>
#include <drm/drm_mode.h>
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <time.h>
#include <unistd.h>

static uint64_t pointer(void *p) { return (uint64_t)(uintptr_t)p; }
int main(void)
{
    int fd = open("/dev/dri/card1", O_RDWR | O_CLOEXEC);
    char name[32] = {0};
    struct drm_version version = {.name = name, .name_len = sizeof(name) - 1};
    struct drm_mode_card_res resources = {0};
    struct drm_mode_get_connector connector = {0};
    struct drm_mode_get_encoder encoder = {0};
    struct drm_mode_crtc original = {0}, off = {0};
    uint32_t *connectors = NULL, selected = 0;
    int result = 1, off_errno = 0;
    if (fd < 0) { perror("open native DRM"); return 1; }
    if (ioctl(fd, DRM_IOCTL_VERSION, &version) || strcmp(name, "msm")) {
        fprintf(stderr, "Native msm DRM required\n"); goto done;
    }
    if (ioctl(fd, DRM_IOCTL_MODE_GETRESOURCES, &resources) ||
        !resources.count_connectors || resources.count_connectors > 32) {
        perror("get resources"); goto done;
    }
    connectors = calloc(resources.count_connectors, sizeof(*connectors));
    if (!connectors) { perror("allocate IDs"); goto done; }
    resources.connector_id_ptr = pointer(connectors);
    /* No encoder/CRTC/FB arrays are requested. */
    resources.count_encoders = resources.count_crtcs = resources.count_fbs = 0;
    if (ioctl(fd, DRM_IOCTL_MODE_GETRESOURCES, &resources)) {
        perror("get connector IDs"); goto done;
    }
    for (unsigned i = 0; i < resources.count_connectors; ++i) {
        connector = (struct drm_mode_get_connector){.connector_id = connectors[i]};
        if (ioctl(fd, DRM_IOCTL_MODE_GETCONNECTOR, &connector)) {
            perror("get connector"); goto done;
        }
        if (connector.connector_type == DRM_MODE_CONNECTOR_DSI &&
            connector.connection == 1 && connector.encoder_id) {
            if (selected) { fprintf(stderr, "Ambiguous active DSI\n"); goto done; }
            selected = connector.connector_id;
            encoder.encoder_id = connector.encoder_id;
        }
    }
    if (!selected || ioctl(fd, DRM_IOCTL_MODE_GETENCODER, &encoder) || !encoder.crtc_id) {
        fprintf(stderr, "No active DSI encoder\n"); goto done;
    }
    original.crtc_id = encoder.crtc_id;
    if (ioctl(fd, DRM_IOCTL_MODE_GETCRTC, &original) || !original.mode_valid ||
        !original.fb_id || original.mode.hdisplay != 1080 || original.mode.vdisplay != 2400) {
        fprintf(stderr, "Unexpected active CRTC/framebuffer\n"); goto done;
    }
    original.set_connectors_ptr = pointer(&selected);
    original.count_connectors = 1;
    off.crtc_id = original.crtc_id;
    printf("Native DSI CRTC=%u original_fb=%u 1080x2400 cycle_once\n", original.crtc_id, original.fb_id);
    fflush(stdout);
    if (ioctl(fd, DRM_IOCTL_MODE_SETCRTC, &off)) { off_errno = errno; perror("disable CRTC"); }
    if (!off_errno) {
        struct timespec pause = {.tv_nsec = 200000000};
        while (nanosleep(&pause, &pause) && errno == EINTR) {}
    }
    /* Always attempt restoration after a submitted disable, including an error. */
    if (ioctl(fd, DRM_IOCTL_MODE_SETCRTC, &original)) { perror("restore original CRTC"); goto done; }
    printf("Original framebuffer and CRTC restored; disable_errno=%d\n", off_errno);
    result = off_errno ? 1 : 0;
done:
    free(connectors);
    close(fd);
    return result;
}
