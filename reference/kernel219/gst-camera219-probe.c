/* Exercise the installed libcamerasrc with a finite, headless appsink stream. */
#include <gst/gst.h>
#include <gst/app/gstappsink.h>
#include <stdio.h>

int main(int argc, char **argv)
{
    if (argc != 2) return 2;
    const char *camera_name = argv[1];
    gst_init(NULL, NULL);
    GstElement *pipeline = gst_pipeline_new(NULL);
    GstElement *source = gst_element_factory_make("libcamerasrc", NULL);
    GstElement *filter = gst_element_factory_make("capsfilter", NULL);
    GstElement *sink = gst_element_factory_make("appsink", NULL);
    if (!pipeline || !source || !filter || !sink) {
        fprintf(stderr, "required GStreamer element missing\n");
        return 3;
    }
    g_object_set(source, "camera-name", camera_name, NULL);
    GstCaps *caps = gst_caps_from_string("video/x-raw,format=RGB,width=2296,height=1728");
    g_object_set(filter, "caps", caps, NULL);
    gst_caps_unref(caps);
    g_object_set(sink, "sync", FALSE, "max-buffers", 2u, "drop", FALSE,
                 "wait-on-eos", FALSE, NULL);
    gst_bin_add_many(GST_BIN(pipeline), source, filter, sink, NULL);
    int result = 0;
    unsigned int frames = 0;
    if (!gst_element_link_many(source, filter, sink, NULL) ||
        gst_element_set_state(pipeline, GST_STATE_PLAYING) == GST_STATE_CHANGE_FAILURE)
        result = 4;
    while (!result && frames < 6) {
        GstSample *sample = gst_app_sink_try_pull_sample(GST_APP_SINK(sink), 5 * GST_SECOND);
        if (!sample) { result = 5; break; }
        GstCaps *actual = gst_sample_get_caps(sample);
        const GstStructure *structure = actual ? gst_caps_get_structure(actual, 0) : NULL;
        int width = 0, height = 0;
        const char *format = structure ? gst_structure_get_string(structure, "format") : NULL;
        GstBuffer *buffer = gst_sample_get_buffer(sample);
        if (!structure || !gst_structure_get_int(structure, "width", &width) ||
            !gst_structure_get_int(structure, "height", &height) || width != 2296 ||
            height != 1728 || !format || g_strcmp0(format, "RGB") ||
            !buffer || gst_buffer_get_size(buffer) != (gsize)2296 * 1728 * 3)
            result = 6;
        gst_sample_unref(sample);
        if (!result) frames++;
    }
    GstBus *bus = gst_element_get_bus(pipeline);
    GstMessage *message;
    unsigned int errors = 0;
    while ((message = gst_bus_pop_filtered(bus, GST_MESSAGE_ERROR))) {
        GError *error = NULL;
        gchar *debug = NULL;
        gst_message_parse_error(message, &error, &debug);
        fprintf(stderr, "GStreamer error: %s\n", error ? error->message : "unknown");
        g_clear_error(&error);g_free(debug);gst_message_unref(message);errors++;
    }
    gst_object_unref(bus);
    if (gst_element_set_state(pipeline, GST_STATE_NULL) == GST_STATE_CHANGE_FAILURE && !result)
        result = 7;
    gst_element_get_state(pipeline, NULL, NULL, 2 * GST_SECOND);
    gst_object_unref(pipeline);
    if (errors && !result) result = 8;
    printf("{\"frames\":%u,\"width\":2296,\"height\":1728,\"format\":\"RGB\",\"bus_errors\":%u}\n", frames, errors);
    return result;
}
