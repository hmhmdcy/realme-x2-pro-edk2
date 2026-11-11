/*
 * samsinkinject - force an RGB texture into gtk4paintablesink.
 *
 * Snapshot 51 displays the viewfinder through camerabin:
 *
 *     pipewiresrc ! ... ! vf-bin(videoconvert ! videoscale) !
 *         aperture-tee ! queue ! gtk4paintablesink
 *
 * gtk4paintablesink advertises many YUV formats before BGRx.  Negotiation
 * therefore hands GTK a YUY2/NV12 GdkMemoryTexture, and the cairo renderer
 * converts that 1080p texture in software on every frame (~5 fps on this
 * device).  A 960x540 BGRx texture takes the direct RGB path, matches the
 * on-screen preview area, and lets the preview run at the source's 30 fps
 * while leaving enough USB input current to keep the battery charging.
 *
 * The preview-appsink in camerabin is *not* the viewfinder: it belongs to
 * camerabin's still-image preview-message pipeline.  Changing its format has
 * no effect on what the user sees.
 *
 * We LD_PRELOAD this library into snapshot and intercept two links:
 *
 *  - viewfinderbin-capsfilter -> vf-bin: disable vf-bin's built-in
 *    videoconvert/videoscale pair, then insert a nearest-neighbour
 *    videoscale and a 960x540 capsfilter so the camera branch is scaled
 *    while it is still NV12.
 *  - anything -> gtk4paintablesink: insert capsfilter(video/x-raw,
 *    format=BGRx, width=960, height=540) so GTK gets a texture it can draw
 *    without a per-frame YUV conversion.
 *
 * SAMURAI_PREVIEW_FORMAT overrides the format (default BGRx).
 * SAMURAI_PREVIEW_WIDTH/HEIGHT override the preview size (default 960x540;
 * set either to 0 to keep the native size).
 * SAMURAI_PREVIEW_SCALE_METHOD overrides the GstVideoScaleMethod (default 0,
 * nearest-neighbour; use 1 for bilinear if more power headroom is available).
 * SAMURAI_SOURCE_WIDTH/HEIGHT optionally lower the camera source caps as
 * well as the display caps.  This lets the sensor use its native low-power
 * mode instead of reading a full-resolution frame and scaling it later.
 * The camera source itself is left at its native still-capture resolution,
 * so photos keep their full resolution unless that option is enabled.
 * SAMURAI_NO_PREVIEW_CONVERT=1 disables the shim.
 * SAMURAI_PREVIEW_DEBUG=1 prints links, negotiated caps and the sink rate.
 */

#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>

#include <gst/gst.h>
#include <glib-object.h>

#define CONV_KEY "samurai-preview-conv"
#define CONV_NAME "samurai-preview-convert-%u"
#define FILTER_NAME "samurai-preview-format-%u"
#define VF_SCALE_KEY "samurai-viewfinder-scale"

typedef gboolean (*LinkPadsFullFn) (GstElement *src, const gchar *srcpad,
                                    GstElement *dst, const gchar *dstpad,
                                    GstPadLinkCheck flags);
typedef gboolean (*LinkFilteredFn) (GstElement *src, GstElement *dst,
                                    GstCaps *caps);
typedef GstPadLinkReturn (*PadLinkFullFn) (GstPad *srcpad, GstPad *sinkpad,
                                           GstPadLinkCheck flags);
typedef void (*ObjectSetPropertyFn) (GObject *object, const gchar *name,
                                     const GValue *value);

/*
 * Set while our own link calls run, so that libgstreamer's internal calls
 * back into the interposed symbols do not try to insert a second converter.
 */
static __thread gint shim_guard = 0;

static gboolean shim_disabled (void)
{
  const gchar *env = g_getenv ("SAMURAI_NO_PREVIEW_CONVERT");

  return env != NULL && *env != '\0' && *env != '0';
}

static void shim_debug (const gchar *format, ...)
{
  va_list args;

  if (g_getenv ("SAMURAI_PREVIEW_DEBUG") == NULL)
    return;

  va_start (args, format);
  vfprintf (stderr, format, args);
  va_end (args);
  fflush (stderr);
}

/*
 * Resolve the real GStreamer entry points.  Everything this shim builds
 * internally must go through these, never through our own exported symbols,
 * or the insertion would recurse into itself.
 */
static LinkPadsFullFn real_link_pads_full (void)
{
  static LinkPadsFullFn fn = NULL;

  if (fn == NULL)
    fn = (LinkPadsFullFn) dlsym (RTLD_NEXT, "gst_element_link_pads_full");

  return fn;
}

static PadLinkFullFn real_pad_link_full (void)
{
  static PadLinkFullFn fn = NULL;

  if (fn == NULL)
    fn = (PadLinkFullFn) dlsym (RTLD_NEXT, "gst_pad_link_full");

  return fn;
}

static ObjectSetPropertyFn real_object_set_property (void)
{
  static ObjectSetPropertyFn fn = NULL;

  if (fn == NULL)
    fn = (ObjectSetPropertyFn) dlsym (RTLD_NEXT, "g_object_set_property");

  return fn;
}

static const gchar *preview_format (void)
{
  const gchar *env = g_getenv ("SAMURAI_PREVIEW_FORMAT");

  return (env != NULL && *env != '\0') ? env : "BGRx";
}

static void
preview_size (gint *width, gint *height)
{
  const gchar *width_env = g_getenv ("SAMURAI_PREVIEW_WIDTH");
  const gchar *height_env = g_getenv ("SAMURAI_PREVIEW_HEIGHT");
  gint w = (width_env && *width_env) ? atoi (width_env) : 960;
  gint h = (height_env && *height_env) ? atoi (height_env) : 540;

  *width = (w > 0) ? w : 0;
  *height = (h > 0) ? h : 0;
}

static gint
preview_scale_method (void)
{
  const gchar *env = g_getenv ("SAMURAI_PREVIEW_SCALE_METHOD");

  return (env && *env) ? atoi (env) : 0;
}

static void
set_int_property_if_present (GstElement *element, const gchar *name, gint value)
{
  if (g_object_class_find_property (G_OBJECT_GET_CLASS (element), name) != NULL)
    g_object_set (G_OBJECT (element), name, value, NULL);
}

static gboolean
source_size (gint *width, gint *height)
{
  const gchar *w_env = g_getenv ("SAMURAI_SOURCE_WIDTH");
  const gchar *h_env = g_getenv ("SAMURAI_SOURCE_HEIGHT");
  gint w = (w_env && *w_env) ? atoi (w_env) : 0;
  gint h = (h_env && *h_env) ? atoi (h_env) : 0;

  if (w <= 0 || h <= 0)
    return FALSE;

  *width = w;
  *height = h;
  return TRUE;
}

static gboolean
caps_are_1080p (GstCaps *caps)
{
  guint i;

  if (caps == NULL)
    return FALSE;

  for (i = 0; i < gst_caps_get_size (caps); i++)
    {
      GstStructure *structure = gst_caps_get_structure (caps, i);
      gint width, height;

      if (gst_structure_get_int (structure, "width", &width) &&
          gst_structure_get_int (structure, "height", &height) &&
          width == 1920 && height == 1080)
        return TRUE;
    }

  return FALSE;
}

static GstCaps *
lower_source_caps (GstCaps *caps, gint width, gint height)
{
  GstCaps *lowered = gst_caps_copy (caps);
  guint i;

  for (i = 0; i < gst_caps_get_size (lowered); i++)
    {
      GstStructure *structure = gst_caps_get_structure (lowered, i);
      gint w, h;

      if (!gst_structure_get_int (structure, "width", &w) ||
          !gst_structure_get_int (structure, "height", &h) ||
          w != 1920 || h != 1080)
        continue;

      gst_structure_set (structure,
                         "width", G_TYPE_INT, width,
                         "height", G_TYPE_INT, height, NULL);
    }

  return lowered;
}

static GstCaps * make_preview_caps (void)
{
  gint w, h;

  preview_size (&w, &h);

  if (w > 0 && h > 0)
    return gst_caps_new_simple ("video/x-raw",
                                "format", G_TYPE_STRING, preview_format (),
                                "width", G_TYPE_INT, w,
                                "height", G_TYPE_INT, h, NULL);

  return gst_caps_new_simple ("video/x-raw",
                              "format", G_TYPE_STRING, preview_format (),
                              NULL);
}

/* gtk4paintablesink is the only element in the pipeline exposing this. */
static gboolean is_paintable_sink (GstElement *element)
{
  if (element == NULL || !GST_IS_ELEMENT (element))
    return FALSE;

  return g_object_class_find_property (G_OBJECT_GET_CLASS (element),
                                       "paintable") != NULL;
}

/*
 * Snapshot wraps gtk4paintablesink in a small ghost-pad bin when the sink
 * already supports YUY2.  The queue therefore links to that bin, not to the
 * paintable sink itself.
 */
static gboolean
contains_paintable_sink (GstElement *element, guint depth)
{
  GstIterator *iter;
  GValue item = G_VALUE_INIT;
  gboolean found = FALSE;

  if (element == NULL || !GST_IS_ELEMENT (element))
    return FALSE;
  if (is_paintable_sink (element))
    return TRUE;
  if (depth == 0 || !GST_IS_BIN (element))
    return FALSE;

  iter = gst_bin_iterate_elements (GST_BIN (element));
  while (!found && gst_iterator_next (iter, &item) == GST_ITERATOR_OK)
    {
      found = contains_paintable_sink (g_value_get_object (&item), depth - 1);
      g_value_reset (&item);
    }
  g_value_unset (&item);
  gst_iterator_free (iter);

  return found;
}

/* Report the format that actually reaches gtk4paintablesink. */
static void
dump_caps (GstElement *element, const gchar *padname, const gchar *what)
{
  GstPad *pad = gst_element_get_static_pad (element, padname);
  GstCaps *caps;
  gchar *text;

  if (pad == NULL)
    return;

  caps = gst_pad_get_current_caps (pad);
  text = caps ? gst_caps_to_string (caps) : g_strdup ("(none)");
  shim_debug ("samsinkinject: %s %s = %s\n", what,
              GST_ELEMENT_NAME (element), text);
  g_free (text);
  if (caps)
    gst_caps_unref (caps);
  gst_object_unref (pad);
}

static gboolean
caps_timeout (gpointer data)
{
  GstElement *element = data;

  if (!GST_IS_ELEMENT (element))
    return G_SOURCE_REMOVE;

  dump_caps (element, "sink", "preview format");
  return G_SOURCE_CONTINUE;
}

typedef struct
{
  gint count;
  gint64 last;
  const gchar *name;
} RateProbe;

static GstPadProbeReturn
rate_probe_cb (GstPad *pad, GstPadProbeInfo *info, gpointer data)
{
  RateProbe *probe = data;

  (void) pad;

  if (GST_PAD_PROBE_INFO_TYPE (info) & GST_PAD_PROBE_TYPE_BUFFER)
    g_atomic_int_inc (&probe->count);

  return GST_PAD_PROBE_OK;
}

static gboolean
rate_report_cb (gpointer data)
{
  RateProbe *probe = data;
  gint64 now = g_get_monotonic_time ();
  gint frames = g_atomic_int_get (&probe->count);
  gdouble elapsed = (now - probe->last) / 1e6;

  g_atomic_int_set (&probe->count, 0);
  probe->last = now;
  shim_debug ("samsinkinject: %s receives %.1f fps (%d frames in %.1fs)\n",
              probe->name, frames / elapsed, frames, elapsed);
  return G_SOURCE_CONTINUE;
}

/* Diagnostic only: how fast does gtk4paintablesink actually get frames? */
static void
install_rate_probe (GstElement *sink)
{
  static GHashTable *probed = NULL;
  GstPad *pad;
  RateProbe *probe;

  if (g_getenv ("SAMURAI_PREVIEW_DEBUG") == NULL)
    return;

  if (probed == NULL)
    probed = g_hash_table_new (g_direct_hash, g_direct_equal);
  if (g_hash_table_contains (probed, sink))
    return;
  g_hash_table_add (probed, sink);

  pad = gst_element_get_static_pad (sink, "sink");
  if (pad == NULL)
    return;

  probe = g_new0 (RateProbe, 1);
  probe->last = g_get_monotonic_time ();
  probe->name = GST_ELEMENT_NAME (sink);
  gst_pad_add_probe (pad, GST_PAD_PROBE_TYPE_BUFFER, rate_probe_cb, probe, g_free);
  gst_object_unref (pad);

  gst_object_ref (sink);
  g_timeout_add_seconds (3, caps_timeout, sink);
  g_timeout_add_seconds (5, rate_report_cb, probe);
}

/*
 * Insert a capsfilter that pins the format GTK can draw directly.  Returns
 * TRUE when src -> capsfilter -> dst is linked.
 */
static gboolean
insert_preview_format_filter (GstElement *src, const gchar *srcpad,
                              GstElement *dst, const gchar *dstpad)
{
  GstObject *parent = gst_object_get_parent (GST_OBJECT (dst));
  GstElement *filter;
  GstCaps *caps;
  LinkPadsFullFn link = real_link_pads_full ();
  gboolean ok;

  if (parent == NULL || !GST_IS_BIN (parent) || link == NULL)
    goto fail;

  filter = gst_element_factory_make ("capsfilter", NULL);
  if (filter == NULL)
    goto fail;

  caps = make_preview_caps ();
  if (caps == NULL)
    goto fail_filter;
  g_object_set (G_OBJECT (filter), "caps", caps, NULL);
  gst_caps_unref (caps);

  gst_object_ref_sink (filter);
  if (!gst_bin_add (GST_BIN (parent), filter))
    goto fail_filter;

  shim_guard++;
  ok = link (src, srcpad, filter, "sink", GST_PAD_LINK_CHECK_DEFAULT) &&
      link (filter, "src", dst, dstpad, GST_PAD_LINK_CHECK_DEFAULT);
  shim_guard--;

  if (!ok)
    {
      gst_bin_remove (GST_BIN (parent), filter);
      gst_object_unref (parent);
      return FALSE;
    }

  gst_object_unref (filter);
  gst_object_unref (parent);
  return TRUE;

fail_filter:
  gst_object_unref (filter);
fail:
  if (parent != NULL)
    gst_object_unref (parent);
  return FALSE;
}

/*
 * Build "videoconvert ! capsfilter" as siblings of @sink and link the chain
 * into @sink.  Returns a reference owned by the caller (the bin owns a
 * second one), or NULL.
 */
static GstElement * build_conversion_chain (GstElement *sink)
{
  GstObject *parent;
  GstElement *conv = NULL;
  GstElement *filter = NULL;
  GstCaps *caps = NULL;
  gchar *name;
  static gint counter = 0;
  LinkPadsFullFn link = real_link_pads_full ();

  if (link == NULL)
    return NULL;

  shim_guard++;

  parent = gst_object_get_parent (GST_OBJECT (sink));
  if (parent == NULL || !GST_IS_BIN (parent))
    goto fail;

  name = g_strdup_printf (CONV_NAME, g_atomic_int_add (&counter, 1));
  conv = gst_element_factory_make ("videoconvert", name);
  g_free (name);

  name = g_strdup_printf (FILTER_NAME, g_atomic_int_add (&counter, 1));
  filter = gst_element_factory_make ("capsfilter", name);
  g_free (name);

  if (conv == NULL || filter == NULL)
    goto fail;

  set_int_property_if_present (conv, "dither", 0);

  caps = make_preview_caps ();
  if (caps == NULL)
    goto fail;
  g_object_set (G_OBJECT (filter), "caps", caps, NULL);
  gst_caps_unref (caps);
  caps = NULL;

  gst_object_ref_sink (conv);
  gst_object_ref_sink (filter);

  if (!gst_bin_add (GST_BIN (parent), conv) ||
      !gst_bin_add (GST_BIN (parent), filter))
    goto fail;

  if (!link (conv, NULL, filter, NULL, GST_PAD_LINK_CHECK_DEFAULT))
    {
      gst_bin_remove (GST_BIN (parent), filter);
      gst_bin_remove (GST_BIN (parent), conv);
      goto fail;
    }

  if (!link (filter, NULL, sink, NULL, GST_PAD_LINK_CHECK_DEFAULT))
    {
      gst_bin_remove (GST_BIN (parent), filter);
      gst_bin_remove (GST_BIN (parent), conv);
      goto fail;
    }

  gst_object_unref (parent);
  gst_object_unref (filter);
  shim_guard--;
  return conv;

fail:
  if (caps != NULL)
    gst_caps_unref (caps);
  if (filter != NULL)
    gst_object_unref (filter);
  if (conv != NULL)
    gst_object_unref (conv);
  if (parent != NULL)
    gst_object_unref (parent);
  shim_guard--;
  return NULL;
}

/* Returns the converter already injected for @sink, if any. */
static GstElement * get_injected_converter (GstElement *sink)
{
  return g_object_get_data (G_OBJECT (sink), CONV_KEY);
}

static GstElement * ensure_converter (GstElement *sink)
{
  GstElement *conv = get_injected_converter (sink);

  if (conv != NULL)
    return conv;

  conv = build_conversion_chain (sink);
  if (conv != NULL)
    g_object_set_data_full (G_OBJECT (sink), CONV_KEY, conv,
                            (GDestroyNotify) gst_object_unref);

  return conv;
}

gboolean
gst_element_link (GstElement *src, GstElement *dst)
{
  LinkPadsFullFn link = real_link_pads_full ();

  shim_debug ("samsinkinject: gst_element_link %s -> %s%s\n",
              GST_ELEMENT_NAME (src), GST_ELEMENT_NAME (dst),
              is_paintable_sink (dst) ? " (paintable)" : "");

  if (link == NULL)
    return FALSE;

  if (!shim_disabled () && contains_paintable_sink (dst, 4))
    {
      install_rate_probe (dst);

      if (insert_preview_format_filter (src, NULL, dst, NULL))
        {
          shim_debug ("samsinkinject: forced %s before %s\n",
                      preview_format (), GST_ELEMENT_NAME (dst));
          return TRUE;
        }

      shim_debug ("samsinkinject: could not force %s before %s\n",
                  preview_format (), GST_ELEMENT_NAME (dst));
    }

  return link (src, NULL, dst, NULL, GST_PAD_LINK_CHECK_DEFAULT);
}

gboolean
gst_element_link_pads (GstElement *src, const gchar *srcpad,
                       GstElement *dst, const gchar *dstpad)
{
  LinkPadsFullFn link = real_link_pads_full ();

  shim_debug ("samsinkinject: gst_element_link_pads %s -> %s%s\n",
              GST_ELEMENT_NAME (src), GST_ELEMENT_NAME (dst),
              is_paintable_sink (dst) ? " (paintable)" : "");

  if (link == NULL)
    return FALSE;

  if (!shim_disabled () && contains_paintable_sink (dst, 4))
    {
      install_rate_probe (dst);

      if (insert_preview_format_filter (src, srcpad, dst, dstpad))
        {
          shim_debug ("samsinkinject: forced %s before %s\n",
                      preview_format (), GST_ELEMENT_NAME (dst));
          return TRUE;
        }
    }

  return link (src, srcpad, dst, dstpad, GST_PAD_LINK_CHECK_DEFAULT);
}

static gboolean insert_viewfinder_scale (GstElement *src,
                                         const gchar *srcpad,
                                         GstElement *dst,
                                         const gchar *dstpad);
static gboolean is_viewfinder_bin (GstElement *element);

gboolean
gst_element_link_pads_full (GstElement *src, const gchar *srcpad,
                            GstElement *dst, const gchar *dstpad,
                            GstPadLinkCheck flags)
{
  LinkPadsFullFn link = real_link_pads_full ();
  gboolean ok;

  if (link == NULL)
    return FALSE;

  shim_debug ("samsinkinject: link_pads_full %s -> %s [%s]%s\n",
              GST_ELEMENT_NAME (src), GST_ELEMENT_NAME (dst),
              G_OBJECT_TYPE_NAME (dst),
              is_paintable_sink (dst) ? " (paintable)" : "");

  if (!shim_disabled () && is_viewfinder_bin (dst))
    {
      if (insert_viewfinder_scale (src, srcpad, dst, dstpad))
        return TRUE;
    }

  if (!shim_disabled () && is_paintable_sink (dst))
    {
      install_rate_probe (dst);

      GstElement *conv = ensure_converter (dst);

      if (conv != NULL)
        {
          shim_guard++;
          ok = link (src, srcpad, conv, NULL, flags);
          shim_guard--;

          if (ok)
            return TRUE;
        }
    }

  return link (src, srcpad, dst, dstpad, flags);
}

gboolean
gst_element_link_filtered (GstElement *src, GstElement *dst, GstCaps *caps)
{
  static LinkFilteredFn real_link_filtered = NULL;

  if (real_link_filtered == NULL)
    real_link_filtered = (LinkFilteredFn) dlsym (RTLD_NEXT,
                                                 "gst_element_link_filtered");
  if (real_link_filtered == NULL)
    return FALSE;

  if (!shim_disabled () && is_paintable_sink (dst))
    {
      GstElement *conv = ensure_converter (dst);
      gboolean ok = FALSE;

      shim_debug ("samsinkinject: link_filtered %s -> paintable sink %s, conv=%p\n",
                  GST_ELEMENT_NAME (src), GST_ELEMENT_NAME (dst), conv);

      if (conv != NULL)
        {
          shim_guard++;
          ok = real_link_filtered (src, conv, caps);
          shim_guard--;
        }

      if (ok)
        return TRUE;
    }

  return real_link_filtered (src, dst, caps);
}

/*
 * camerabin connects its viewfinder queue to the sink with gst_pad_link(),
 * so the insertion has to happen here.
 */
GstPadLinkReturn
gst_pad_link_full (GstPad *srcpad, GstPad *sinkpad, GstPadLinkCheck flags)
{
  PadLinkFullFn real_pad_link = real_pad_link_full ();

  if (real_pad_link == NULL)
    return GST_PAD_LINK_REFUSED;

  if (shim_guard == 0 && !shim_disabled ())
    {
      GstObject *parent = gst_pad_get_parent (sinkpad);

      if (parent != NULL && GST_IS_ELEMENT (parent) &&
          is_paintable_sink (GST_ELEMENT (parent)))
        {
          GstElement *sink = GST_ELEMENT (parent);
          GstElement *conv = ensure_converter (sink);

          shim_debug ("samsinkinject: pad link %s:%s -> paintable sink %s, conv=%p\n",
                      GST_ELEMENT_NAME (GST_PAD_PARENT (srcpad)),
                      GST_PAD_NAME (srcpad), GST_ELEMENT_NAME (sink), conv);

          if (conv != NULL)
            {
              GstPad *convpad = gst_element_get_static_pad (conv, "sink");

              if (convpad != NULL)
                {
                  GstPadLinkReturn ret;

                  shim_guard++;
                  ret = real_pad_link (srcpad, convpad, flags);
                  shim_guard--;
                  gst_object_unref (convpad);
                  gst_object_unref (parent);

                  if (ret == GST_PAD_LINK_OK)
                    return ret;

                  return real_pad_link (srcpad, sinkpad, flags);
                }
            }
        }

      if (parent != NULL)
        gst_object_unref (parent);
    }

  return real_pad_link (srcpad, sinkpad, flags);
}

GstPadLinkReturn
gst_pad_link (GstPad *srcpad, GstPad *sinkpad)
{
  return gst_pad_link_full (srcpad, sinkpad, GST_PAD_LINK_CHECK_DEFAULT);
}

/*
 * Aperture asks for camera.best_caps(), which is the largest 16:9 mode up
 * to 1080p.  Optionally lower the camera-source capsfilter to 720p before
 * libcamera negotiates a sensor mode.  The sensor can then use its native
 * 1280x720 mode instead of reading a full-resolution frame for preview.
 */
void
g_object_set_property (GObject *object, const gchar *name, const GValue *value)
{
  ObjectSetPropertyFn set_property = real_object_set_property ();
  gint width, height;

  if (set_property == NULL)
    return;

  if (!shim_disabled () && shim_guard == 0 &&
      g_strcmp0 (name, "caps") == 0 &&
      G_IS_OBJECT (object) && GST_IS_ELEMENT (object) &&
      g_strcmp0 (G_OBJECT_TYPE_NAME (object), "GstCapsFilter") == 0 &&
      G_VALUE_HOLDS (value, GST_TYPE_CAPS) &&
      source_size (&width, &height))
    {
      GstCaps *caps = g_value_get_boxed (value);

      if (caps_are_1080p (caps))
        {
          GstCaps *lowered = lower_source_caps (caps, width, height);
          GValue replacement = G_VALUE_INIT;

          g_value_init (&replacement, GST_TYPE_CAPS);
          g_value_set_boxed (&replacement, lowered);
          shim_guard++;
          set_property (object, name, &replacement);
          shim_guard--;
          g_value_unset (&replacement);
          gst_caps_unref (lowered);
          shim_debug ("samsinkinject: lowered source caps to %dx%d\n",
                      width, height);
          return;
        }
    }

  set_property (object, name, value);
}

/*
 * camerabin links its viewfinder caps filter straight into GstViewfinderBin,
 * whose internal videoconvert runs before its videoscale.  At 1080p that
 * means converting a 1080p YUV frame to RGB and only then scaling it down,
 * which is the expensive order.  Insert a bilinear videoscale and a 720p
 * capsfilter in front of the viewfinder bin so the scaling happens while the
 * frame is still NV12.
 */
static gboolean
is_viewfinder_bin (GstElement *element)
{
  if (element == NULL || !GST_IS_ELEMENT (element))
    return FALSE;

  return g_strcmp0 (g_type_name (G_OBJECT_TYPE (element)),
                     "GstViewfinderBin") == 0;
}

static gboolean
insert_viewfinder_scale (GstElement *src, const gchar *srcpad,
                          GstElement *dst, const gchar *dstpad)
{
  GstObject *parent;
  GstElement *scale = NULL;
  GstElement *filter = NULL;
  GstCaps *caps;
  LinkPadsFullFn link = real_link_pads_full ();
  gint width, height;
  gboolean ok;
  gboolean scale_added = FALSE;
  gboolean filter_added = FALSE;
  gboolean converters_disabled = FALSE;

  if (link == NULL || g_object_get_data (G_OBJECT (dst), VF_SCALE_KEY) != NULL)
    return FALSE;

  parent = gst_object_get_parent (GST_OBJECT (dst));
  if (parent == NULL || !GST_IS_BIN (parent))
    {
      if (parent != NULL)
        gst_object_unref (parent);
      return FALSE;
    }

  preview_size (&width, &height);
  if (width <= 0 || height <= 0)
    {
      gst_object_unref (parent);
      return FALSE;
    }

  scale = gst_element_factory_make ("videoscale", NULL);
  filter = gst_element_factory_make ("capsfilter", NULL);
  if (scale == NULL || filter == NULL)
    goto fail;

  /* The app's vf-bin normally owns both the converter and the scaler.  We
   * provide the complete YUV-scale -> RGB-convert chain ourselves, so its
   * built-in pair would only add another full-frame copy. */
  if (g_object_class_find_property (G_OBJECT_GET_CLASS (dst),
                                    "disable-converters") != NULL)
    {
      g_object_set (G_OBJECT (dst), "disable-converters", TRUE, NULL);
      converters_disabled = TRUE;
    }

  set_int_property_if_present (scale, "method", preview_scale_method ());
  set_int_property_if_present (scale, "dither", 0);

  caps = gst_caps_new_simple ("video/x-raw",
                              "width", G_TYPE_INT, width,
                              "height", G_TYPE_INT, height, NULL);
  g_object_set (G_OBJECT (filter), "caps", caps, NULL);
  gst_caps_unref (caps);

  gst_object_ref_sink (scale);
  gst_object_ref_sink (filter);

  if (!gst_bin_add (GST_BIN (parent), scale))
    goto fail;
  scale_added = TRUE;
  if (!gst_bin_add (GST_BIN (parent), filter))
    goto fail;
  filter_added = TRUE;

  shim_guard++;
  ok = link (src, srcpad, scale, "sink", GST_PAD_LINK_CHECK_DEFAULT) &&
      link (scale, "src", filter, "sink", GST_PAD_LINK_CHECK_DEFAULT) &&
      link (filter, "src", dst, dstpad, GST_PAD_LINK_CHECK_DEFAULT);
  shim_guard--;

  if (!ok)
    goto fail;

  g_object_set_data_full (G_OBJECT (dst), VF_SCALE_KEY,
                          gst_object_ref (filter),
                          (GDestroyNotify) gst_object_unref);
  shim_debug ("samsinkinject: inserted %dx%d videoscale(method=%d) before %s\n",
              width, height, preview_scale_method (), GST_ELEMENT_NAME (dst));

  gst_object_unref (filter);
  gst_object_unref (scale);
  gst_object_unref (parent);
  return TRUE;

fail:
  if (converters_disabled)
    g_object_set (G_OBJECT (dst), "disable-converters", FALSE, NULL);
  if (filter_added)
    gst_bin_remove (GST_BIN (parent), filter);
  if (scale_added)
    gst_bin_remove (GST_BIN (parent), scale);
  if (filter != NULL)
    gst_object_unref (filter);
  if (scale != NULL)
    gst_object_unref (scale);
  gst_object_unref (parent);
  return FALSE;
}
