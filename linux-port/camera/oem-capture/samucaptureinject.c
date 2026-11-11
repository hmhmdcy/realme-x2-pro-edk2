/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * Replace Snapshot's native still with the OEM dual-stream/64MP capture.
 *
 * Snapshot first takes its normal 1440x1080 still so it creates the gallery
 * entry and filename.  We hold the resulting picture-done signal, replace the
 * file with samurai-oem-capture output, then re-emit picture-done.  The gallery
 * therefore loads the full-resolution JPEG and the photo stays in
 * ~/Pictures/Camera.
 */

#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct _GstElement GstElement;
typedef struct _GThread GThread;
typedef unsigned int guint;
typedef unsigned long gulong;
typedef int gint;
typedef int gboolean;
typedef char gchar;
typedef void *gpointer;

/* GValue is 24 bytes on AArch64 LP64 and is public ABI. */
typedef struct _GValue {
	unsigned long g_type;
	unsigned long data[2];
} GValue;

extern const gchar *g_signal_name(guint signal_id);
extern gpointer g_value_get_object(const GValue *value);
extern gpointer g_object_ref(gpointer object);
extern void g_object_unref(gpointer object);
extern void g_object_get(gpointer object, const gchar *first_property_name, ...);
extern void g_signal_emit_by_name(gpointer instance,
				  const gchar *detailed_signal, ...);
extern guint g_idle_add(gboolean (*function)(gpointer data), gpointer data);
extern void g_free(gpointer mem);
extern GThread *g_thread_new(const gchar *name,
			     gpointer (*func)(gpointer), gpointer data);
extern void g_usleep(gulong microseconds);
extern gboolean g_spawn_command_line_sync(const gchar *command_line,
					  gchar **standard_output,
					  gchar **standard_error,
					  gint *wait_status, void **error);
extern int gst_element_set_state(GstElement *element, int state);

static GstElement *snapshot_pipeline;
static GstElement *snapshot_camerabin;
static GstElement *pending_camerabin;
static gchar *pending_path;
static volatile int capture_busy;

struct capture_job {
	GstElement *camerabin;
	gpointer viewfinder;
	gpointer file;
	gchar *path;
};

static gboolean emit_picture_done(gpointer data)
{
	struct capture_job *job = data;

	if (job->file)
		g_signal_emit_by_name(job->viewfinder, "picture-done", job->file);
	if (job->viewfinder)
		g_object_unref(job->viewfinder);
	if (job->file)
		g_object_unref(job->file);
	g_free(job->path);
	g_free(job);
	capture_busy = 0;
	return 0;
}

static gpointer capture_worker(gpointer data)
{
	struct capture_job *job = data;
	GstElement *element = job->camerabin ? job->camerabin :
			      snapshot_camerabin;
	const gchar *highres = getenv("SAMURAI_HIGHRES_ON_SHUTTER");
	gint status = -1;

	if (highres && strcmp(highres, "1") == 0) {
		setenv("SAMURAI_HIGHRES", "1", 1);
		fprintf(stderr, "samucapture: replacing native photo with OEM 64MP\n");
	} else {
		fprintf(stderr, "samucapture: replacing native photo with OEM 4608x3456\n");
	}
	fprintf(stderr, "samucapture: target=%s\n",
		job->path ? job->path : "(none)");

	if (element)
		gst_element_set_state(element, 1);
	g_usleep(5000000);

	unsetenv("LD_PRELOAD");
	setenv("SAMURAI_ALLOW_SNAPSHOT", "1", 1);
	if (job->path)
		setenv("SAMURAI_FINAL_JPEG", job->path, 1);
	if (!g_spawn_command_line_sync("/usr/local/bin/samurai-oem-capture",
				       NULL, NULL, &status, NULL))
		fprintf(stderr, "samucapture: spawn failed\n");
	else
		fprintf(stderr, "samucapture: capture status=%d\n", status);

	if (highres && strcmp(highres, "1") == 0) {
		status = -1;
		g_spawn_command_line_sync(
			"setsid /usr/local/bin/samurai-restart-snapshot "
			">/dev/null 2>&1 &", NULL, NULL, &status, NULL);
		fprintf(stderr, "samucapture: restart snapshot status=%d\n",
			status);
		if (job->camerabin)
			g_object_unref(job->camerabin);
		if (job->viewfinder)
			g_object_unref(job->viewfinder);
		if (job->file)
			g_object_unref(job->file);
		g_free(job->path);
		g_free(job);
		return NULL;
	}

	g_usleep(1000000);
	if (element)
		gst_element_set_state(element, 4);
	if (job->camerabin)
		g_object_unref(job->camerabin);

	if (!g_idle_add(emit_picture_done, job))
		emit_picture_done(job);
	return NULL;
}

static gboolean is_image_mode(gpointer instance)
{
	gint mode = 0;

	g_object_get(instance, "mode", &mode, NULL);
	return mode == 1;
}

void g_signal_emitv(const GValue *instance_and_params, guint signal_id,
		    guint detail, GValue *return_value)
{
	static void (*real_emitv)(const GValue *, guint, guint, GValue *);
	const gchar *name = g_signal_name(signal_id);
	const gchar *capture_on_shutter = getenv("SAMURAI_CAPTURE_ON_SHUTTER");
	gboolean enabled = capture_on_shutter &&
			   strcmp(capture_on_shutter, "1") == 0;

	if (!real_emitv)
		real_emitv = dlsym(RTLD_NEXT, "g_signal_emitv");

	if (enabled && name && strcmp(name, "start-capture") == 0 &&
	    !capture_busy) {
		gpointer instance = g_value_get_object(instance_and_params);

		if (instance && is_image_mode(instance)) {
			gchar *path = NULL;

			g_object_get(instance, "location", &path, NULL);
			g_free(pending_path);
			pending_path = path;
			pending_camerabin = g_object_ref(instance);
			capture_busy = 1;
			if (real_emitv)
				real_emitv(instance_and_params, signal_id, detail,
					   return_value);
			return;
		}
	}

	if (enabled && name && strcmp(name, "picture-done") == 0 &&
	    capture_busy && pending_camerabin) {
		gpointer viewfinder = g_value_get_object(instance_and_params);
		gpointer file = g_value_get_object(&instance_and_params[1]);

		if (viewfinder && file && pending_path) {
			struct capture_job *job = calloc(1, sizeof(*job));

			if (job) {
				job->camerabin = pending_camerabin;
				job->viewfinder = g_object_ref(viewfinder);
				job->file = g_object_ref(file);
				job->path = pending_path;
				pending_camerabin = NULL;
				pending_path = NULL;
				g_thread_new("samucapture", capture_worker, job);
				return;
			}
		}
		if (pending_camerabin) {
			g_object_unref(pending_camerabin);
			pending_camerabin = NULL;
		}
		g_free(pending_path);
		pending_path = NULL;
		capture_busy = 0;
	}

	if (real_emitv)
		real_emitv(instance_and_params, signal_id, detail, return_value);
}

GstElement *gst_pipeline_new(const gchar *name)
{
	static GstElement *(*real_new)(const gchar *);
	GstElement *pipeline;

	if (!real_new)
		real_new = dlsym(RTLD_NEXT, "gst_pipeline_new");
	pipeline = real_new ? real_new(name) : NULL;
	if (pipeline)
		snapshot_pipeline = pipeline;
	return pipeline;
}

GstElement *gst_element_factory_make(const gchar *factoryname,
				     const gchar *name)
{
	static GstElement *(*real_make)(const gchar *, const gchar *);
	GstElement *element;

	if (!real_make)
		real_make = dlsym(RTLD_NEXT, "gst_element_factory_make");
	element = real_make ? real_make(factoryname, name) : NULL;
	if (element && factoryname && strcmp(factoryname, "camerabin") == 0)
		snapshot_camerabin = element;
	return element;
}
