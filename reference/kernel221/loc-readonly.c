/* Read-only LOC extensions from Qualcomm's public IDL. No SET/START or NV APIs. */
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wdeprecated-declarations"
#include <libqmi-glib.h>
#include <libqrtr-glib.h>
#pragma GCC diagnostic pop
#include <stdio.h>
#include <string.h>

static GMainLoop *loop;
static GAsyncResult *completed;
static void ready(GObject *source, GAsyncResult *result, gpointer unused)
{
    (void)source; (void)unused;
    completed = g_object_ref(result);
    g_main_loop_quit(loop);
}
static GAsyncResult *wait_result(void)
{
    g_main_loop_run(loop);
    return g_steal_pointer(&completed);
}
typedef struct {
    guint16 message_id;
    guint8 cid;
    QmiMessage *indication;
    gint64 received_us;
    gboolean waiting_indication;
} Query;
static void indication(QmiDevice *device, QmiMessage *message, gpointer data)
{
    (void)device;
    Query *q = data;
    if (qmi_message_get_service(message) != QMI_SERVICE_LOC ||
        qmi_message_get_client_id(message) != q->cid ||
        qmi_message_get_message_id(message) != q->message_id)
        return;
    if (!q->indication) {
        q->indication = qmi_message_ref(message);
        q->received_us = g_get_monotonic_time();
        if (q->waiting_indication) g_main_loop_quit(loop);
    }
}
static gboolean deadline(gpointer unused)
{
    (void)unused; g_main_loop_quit(loop); return G_SOURCE_REMOVE;
}
typedef struct { gboolean first; } Printer;
static void print_tlv(guint8 type, const guint8 *value, gsize length, gpointer data)
{
    Printer *p = data;
    printf("%s\"%u\":\"", p->first ? "" : ",", type); p->first = FALSE;
    for (gsize i = 0; i < length; i++) printf("%02x", value[i]);
    printf("\"");
}
static gboolean query(QmiDevice *device, QmiClient *client, guint16 id)
{
    Query q = { .message_id = id, .cid = qmi_client_get_cid(client) };
    gulong handler = g_signal_connect(device, QMI_DEVICE_SIGNAL_INDICATION, G_CALLBACK(indication), &q);
    guint16 transaction_id = qmi_client_get_next_transaction_id(client);
    QmiMessage *request = qmi_message_new(QMI_SERVICE_LOC, q.cid, transaction_id, id);
    GError *error = NULL;
    qmi_device_command_full(device, request, NULL, 10, NULL, ready, NULL);
    GAsyncResult *result = wait_result();
    QmiMessage *ack = qmi_device_command_full_finish(device, result, &error);
    gint64 ack_us = g_get_monotonic_time();
    g_object_unref(result); qmi_message_unref(request);
    guint16 length = 0, ack_result = 65535, ack_error = 65535;
    const guint8 *value = ack ? qmi_message_get_raw_tlv(ack, 2, &length) : NULL;
    gboolean matching_ack = ack && qmi_message_get_service(ack) == QMI_SERVICE_LOC &&
        qmi_message_get_client_id(ack) == q.cid && qmi_message_get_message_id(ack) == id &&
        qmi_message_get_transaction_id(ack) == transaction_id;
    if (matching_ack && value && length == 4) {
        ack_result = value[0] | (value[1] << 8);
        ack_error = value[2] | (value[3] << 8);
    }
    if (ack_result == 0 && !q.indication) {
        q.waiting_indication = TRUE;
        guint timer = g_timeout_add_seconds(12, deadline, NULL);
        g_main_loop_run(loop);
        q.waiting_indication = FALSE;
        if (g_main_context_find_source_by_id(NULL, timer)) g_source_remove(timer);
    }
    g_signal_handler_disconnect(device, handler);
    printf("{\"kind\":\"query\",\"message_id\":%u,\"transport_ok\":%s,"
           "\"matching_ack\":%s,\"ack_result\":%u,\"ack_error\":%u,\"indication_received\":%s,"
           "\"indication_before_ack\":%s,\"ind_tlvs\":{", id,
           ack ? "true" : "false", matching_ack ? "true" : "false", ack_result, ack_error,
           q.indication ? "true" : "false",
           q.indication && q.received_us <= ack_us ? "true" : "false");
    Printer printer = { .first = TRUE };
    if (q.indication) qmi_message_foreach_raw_tlv(q.indication, print_tlv, &printer);
    printf("}}\n"); fflush(stdout);
    if (error) { g_printerr("LOC query failed: %s\n", error->message); g_clear_error(&error); }
    if (ack) qmi_message_unref(ack);
    gboolean received = q.indication != NULL;
    if (q.indication) qmi_message_unref(q.indication);
    return matching_ack && ack_result <= 1 && (ack_result != 0 || received);
}
int main(void)
{
    GError *error = NULL; GAsyncResult *result;
    QrtrBus *bus = NULL; QmiDevice *device = NULL; QmiClient *client = NULL;
    gboolean success = FALSE, opened = FALSE, released = FALSE, closed = FALSE;
    loop = g_main_loop_new(NULL, FALSE);
    qrtr_bus_new(2000, NULL, ready, NULL); result = wait_result();
    bus = qrtr_bus_new_finish(result, &error); g_object_unref(result);
    if (!bus) goto cleanup;
    QrtrNode *node = qrtr_bus_get_node(bus, 0);
    if (!node) goto cleanup;
    qmi_device_new_from_node(node, NULL, ready, NULL); result = wait_result();
    device = qmi_device_new_from_node_finish(result, &error); g_object_unref(result);
    if (!device) goto cleanup;
    qmi_device_open(device, QMI_DEVICE_OPEN_FLAGS_EXPECT_INDICATIONS, 10, NULL, ready, NULL);
    result = wait_result(); opened = qmi_device_open_finish(device, result, &error); g_object_unref(result);
    if (!opened) goto cleanup;
    qmi_device_allocate_client(device, QMI_SERVICE_LOC, QMI_CID_NONE, 10, NULL, ready, NULL);
    result = wait_result(); client = qmi_device_allocate_client_finish(device, result, &error); g_object_unref(result);
    if (!client) goto cleanup;
    /* Known typed query first verifies the raw indication path on this firmware. */
    if (!query(device, client, 0x004b)) goto cleanup;
    if (!query(device, client, 0x00bf)) goto cleanup;
    if (!query(device, client, 0x00b7)) goto cleanup;
    if (!query(device, client, 0x00e1)) goto cleanup;
    success = TRUE;
cleanup:
    if (error) { g_printerr("LOC lifecycle: %s\n", error->message); g_clear_error(&error); }
    if (client) {
        qmi_device_release_client(device, client, QMI_DEVICE_RELEASE_CLIENT_FLAGS_RELEASE_CID, 10, NULL, ready, NULL);
        result = wait_result(); released = qmi_device_release_client_finish(device, result, &error); g_object_unref(result);
        if (error) g_clear_error(&error);
        g_clear_object(&client);
    }
    if (opened) {
        qmi_device_close_async(device, 10, NULL, ready, NULL); result = wait_result();
        closed = qmi_device_close_finish(device, result, &error); g_object_unref(result);
        if (error) g_clear_error(&error);
    }
    printf("{\"kind\":\"cleanup\",\"queries_complete\":%s,\"client_released\":%s,\"device_closed\":%s}\n",
           success ? "true" : "false", released ? "true" : "false", closed ? "true" : "false");
    g_clear_object(&device); g_clear_object(&bus); g_main_loop_unref(loop);
    return success && released && closed ? 0 : 1;
}
