#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>

#include <gst/gst.h>
#include <glib-object.h>

typedef void (*ObjectSetPropertyFn) (GObject *object, const gchar *name,
                                     const GValue *value);

static gboolean
caps_have_size (GstCaps *caps, gint width, gint height)
{
  guint i;

  for (i = 0; i < gst_caps_get_size (caps); i++)
    {
      GstStructure *structure = gst_caps_get_structure (caps, i);
      gint w, h;

      if (gst_structure_get_int (structure, "width", &w) &&
          gst_structure_get_int (structure, "height", &h) &&
          w == width && h == height)
        return TRUE;
    }

  return FALSE;
}

static GstCaps *
prefer_source_caps (GstCaps *caps, gint width, gint height, gint framerate)
{
  GstCaps *result;
  GstStructure *preferred = NULL;
  GstStructure *fallback = NULL;
  guint i;

  for (i = 0; i < gst_caps_get_size (caps); i++)
    {
      GstStructure *structure = gst_caps_get_structure (caps, i);
      gint w, h;

      if (!gst_structure_get_int (structure, "width", &w) ||
          !gst_structure_get_int (structure, "height", &h))
        continue;
      if (w == width && h == height)
        {
          preferred = gst_structure_copy (structure);
          break;
        }
      if (fallback == NULL && w == 1920 && h == 1080)
        fallback = gst_structure_copy (structure);
    }

  if (preferred == NULL && fallback == NULL)
    {
      if (fallback != NULL)
        gst_structure_free (fallback);
      return NULL;
    }

  if (preferred == NULL)
    {
      preferred = fallback;
      gst_structure_set (preferred,
                         "width", G_TYPE_INT, width,
                         "height", G_TYPE_INT, height,
                         NULL);
    }
  else if (fallback != NULL)
    {
      gst_structure_free (fallback);
    }

  gst_structure_set (preferred,
                     "framerate", GST_TYPE_FRACTION, framerate, 1,
                     NULL);

  result = gst_caps_new_empty ();
  gst_caps_append_structure (result, preferred);

  for (i = 0; i < gst_caps_get_size (caps); i++)
    {
      GstStructure *structure = gst_caps_get_structure (caps, i);
      gint w, h;

      if (gst_structure_get_int (structure, "width", &w) &&
          gst_structure_get_int (structure, "height", &h) &&
          w == width && h == height)
        continue;
      gst_caps_append_structure (result, gst_structure_copy (structure));
    }

  return result;
}

void
g_object_set_property (GObject *object, const gchar *name,
                       const GValue *value)
{
  static ObjectSetPropertyFn real_set_property;
  const gchar *mode;
  gint width, height, framerate;
  GstCaps *caps;
  GstCaps *preferred;

  if (real_set_property == NULL)
    real_set_property = (ObjectSetPropertyFn) dlsym (RTLD_NEXT,
                                                    "g_object_set_property");
  if (real_set_property == NULL)
    return;

  mode = g_getenv ("SAMURAI_PREFER_SOURCE");
  if (mode == NULL ||
      sscanf (mode, "%dx%d@%d", &width, &height, &framerate) != 3 ||
      width <= 0 || height <= 0 || framerate <= 0 ||
      g_strcmp0 (name, "caps") != 0 ||
      !G_IS_OBJECT (object) || !GST_IS_ELEMENT (object) ||
      g_strcmp0 (G_OBJECT_TYPE_NAME (object), "GstCapsFilter") != 0 ||
      !G_VALUE_HOLDS (value, GST_TYPE_CAPS))
    {
      real_set_property (object, name, value);
      return;
    }

  caps = g_value_get_boxed (value);
  if (caps == NULL || gst_caps_get_size (caps) < 8 ||
      !caps_have_size (caps, 1920, 1080))
    {
      real_set_property (object, name, value);
      return;
    }

  preferred = prefer_source_caps (caps, width, height, framerate);
  if (preferred == NULL)
    {
      real_set_property (object, name, value);
      return;
    }

  GValue replacement = G_VALUE_INIT;
  g_value_init (&replacement, GST_TYPE_CAPS);
  g_value_set_boxed (&replacement, preferred);
  real_set_property (object, name, &replacement);
  g_value_unset (&replacement);
  gst_caps_unref (preferred);

  if (g_getenv ("SAMURAI_CAPS_DEBUG") != NULL)
    {
      gchar *text = gst_caps_to_string (caps);
      g_printerr ("samucapsinject: preferred %dx%d@%d over %s\n",
                  width, height, framerate, text);
      g_free (text);
    }
}
