/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * Register jifmux before libgstcamerabin.so is scanned.
 *
 * On this image libgstcamerabin's encodebin caches the factory list during
 * plugin init. The scan reaches camerabin before jpegformat, so jifmux is
 * reported as an unknown factory and camerabin never reaches Playing.
 *
 * Hook the registry scan (which runs inside the application's own gst_init)
 * and load jpegformat once before the real scan starts. This is deliberately
 * not a constructor: initializing GStreamer before the application breaks
 * the Rust bindings' pad-template setup.
 */

#define _GNU_SOURCE
#include <dlfcn.h>
#include <stddef.h>

typedef char gchar;
typedef int gboolean;
typedef struct _GstRegistry GstRegistry;

extern void *gst_plugin_load_file(const gchar *filename, void **error);
extern gboolean gst_registry_scan_path(GstRegistry *registry,
				       const gchar *path);

gboolean gst_registry_scan_path(GstRegistry *registry, const gchar *path)
{
	static gboolean (*real_scan)(GstRegistry *, const gchar *);
	static int loaded;

	if (!real_scan)
		real_scan = dlsym(RTLD_NEXT, "gst_registry_scan_path");
	if (!loaded) {
		loaded = 1;
		gst_plugin_load_file("/usr/lib/gstreamer-1.0/libgstjpegformat.so",
				     NULL);
	}
	return real_scan ? real_scan(registry, path) : 0;
}
