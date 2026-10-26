/* Bounded same-CID LOC observation. Only GET, REGISTER, START and STOP. No NV. */
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wdeprecated-declarations"
#include <libqmi-glib.h>
#include <libqrtr-glib.h>
#pragma GCC diagnostic pop
#include <glib-unix.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>

static GMainLoop *loop;
static GAsyncResult *completed;
static gint64 began;
static gboolean interrupted, observing, ambiguous_query;
static guint8 cid;
static guint16 pending_id;
static QmiMessage *pending_indication;
static gboolean awaiting_indication;

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
static gboolean deadline(gpointer unused)
{
    (void)unused;
    g_main_loop_quit(loop);
    return G_SOURCE_REMOVE;
}
static gboolean interrupted_cb(gpointer unused)
{
    (void)unused;
    interrupted = TRUE;
    if (observing) g_main_loop_quit(loop);
    return G_SOURCE_CONTINUE;
}
static void pump(guint seconds)
{
    guint timer = g_timeout_add_seconds(seconds, deadline, NULL);
    observing = TRUE;
    g_main_loop_run(loop);
    observing = FALSE;
    if (g_main_context_find_source_by_id(NULL, timer)) g_source_remove(timer);
}
typedef struct { gboolean first; } Printer;
static void print_tlv(guint8 type, const guint8 *value, gsize length, gpointer data)
{
    Printer *p = data;
    printf("%s\"%u\":\"", p->first ? "" : ",", type);
    p->first = FALSE;
    for (gsize i = 0; i < length; i++) printf("%02x", value[i]);
    printf("\"");
}
static void print_tlvs(QmiMessage *message)
{
    Printer p = { .first = TRUE };
    printf("{");
    if (message) qmi_message_foreach_raw_tlv(message, print_tlv, &p);
    printf("}");
}
static void indication(QmiDevice *device, QmiMessage *message, gpointer unused)
{
    (void)device; (void)unused;
    if (qmi_message_get_service(message) != QMI_SERVICE_LOC || qmi_message_get_client_id(message) != cid)
        return;
    guint16 id = qmi_message_get_message_id(message);
    printf("{\"kind\":\"indication\",\"message_id\":%u,\"elapsed_us\":%" G_GINT64_FORMAT ",\"tlvs\":",
           id, g_get_monotonic_time() - began);
    print_tlvs(message); printf("}\n"); fflush(stdout);
    if (pending_id && id == pending_id && !pending_indication) {
        pending_indication = qmi_message_ref(message);
        if (awaiting_indication) g_main_loop_quit(loop);
    }
}
static guint32 read_u32(QmiMessage *message, guint8 tag, guint32 absent)
{
    guint16 length = 0;
    const guint8 *v = message ? qmi_message_get_raw_tlv(message, tag, &length) : NULL;
    return v && length == 4 ? ((guint32)v[0] | ((guint32)v[1] << 8) | ((guint32)v[2] << 16) | ((guint32)v[3] << 24)) : absent;
}
static void add_bytes(QmiMessage *request, guint8 tag, const guint8 *value, gsize length)
{
    GError *error = NULL;
    if (!qmi_message_add_raw_tlv(request, tag, value, length, &error))
        g_error("Could not construct fixed LOC request: %s", error->message);
}
static void add_u32(QmiMessage *request, guint8 tag, guint32 value)
{
    guint32 little = GUINT32_TO_LE(value);
    add_bytes(request, tag, (const guint8 *)&little, sizeof(little));
}
static QmiMessage *request_new(QmiClient *client, guint16 id)
{
    return qmi_message_new(QMI_SERVICE_LOC, cid, qmi_client_get_next_transaction_id(client), id);
}
static gboolean command(QmiDevice *device, QmiMessage *request, gboolean need_indication, guint32 *value)
{
    GError *error = NULL;
    guint16 id = qmi_message_get_message_id(request);
    guint16 transaction = qmi_message_get_transaction_id(request);
    g_clear_pointer(&pending_indication, qmi_message_unref);
    pending_id = need_indication ? id : 0;
    qmi_device_command_full(device, request, NULL, 10, NULL, ready, NULL);
    GAsyncResult *result = wait_result();
    QmiMessage *ack = qmi_device_command_full_finish(device, result, &error);
    g_object_unref(result);
    guint16 length = 0, ack_result = 65535, ack_error = 65535;
    const guint8 *v = ack ? qmi_message_get_raw_tlv(ack, 2, &length) : NULL;
    gboolean match = ack && qmi_message_get_service(ack) == QMI_SERVICE_LOC &&
        qmi_message_get_client_id(ack) == cid && qmi_message_get_message_id(ack) == id &&
        qmi_message_get_transaction_id(ack) == transaction;
    if (match && v && length == 4) {
        ack_result = v[0] | (v[1] << 8);
        ack_error = v[2] | (v[3] << 8);
    }
    if (need_indication && ack_result == 0 && !pending_indication) {
        guint timer = g_timeout_add_seconds(12, deadline, NULL);
        awaiting_indication = TRUE;
        g_main_loop_run(loop);
        awaiting_indication = FALSE;
        if (g_main_context_find_source_by_id(NULL, timer)) g_source_remove(timer);
    }
    guint32 status = read_u32(pending_indication, 1, G_MAXUINT32);
    if (need_indication && ack_result == 0 && !pending_indication) ambiguous_query = TRUE;
    if (value) *value = read_u32(pending_indication, id == 0x0032 ? 2 : 16, G_MAXUINT32);
    printf("{\"kind\":\"command\",\"message_id\":%u,\"matching_ack\":%s,"
           "\"ack_result\":%u,\"ack_error\":%u,\"indication_received\":%s,"
           "\"indication_status\":%u,\"request_tlvs\":", id, match ? "true" : "false",
           ack_result, ack_error, pending_indication ? "true" : "false", status);
    print_tlvs(request); printf(",\"ind_tlvs\":"); print_tlvs(pending_indication); printf("}\n"); fflush(stdout);
    if (error) { g_printerr("LOC command: %s\n", error->message); g_clear_error(&error); }
    gboolean ok = match && ack_result == 0 && (!need_indication || (pending_indication && status == 0));
    pending_id = 0;
    g_clear_pointer(&pending_indication, qmi_message_unref);
    if (ack) qmi_message_unref(ack);
    qmi_message_unref(request);
    return ok;
}
int main(int argc, char **argv)
{
    if (argc != 2 || (strcmp(argv[1], "probe") && strcmp(argv[1], "default") && strcmp(argv[1], "high") && strcmp(argv[1], "oem")))
        return 2;
    gboolean probe = !strcmp(argv[1], "probe"), high = !strcmp(argv[1], "high") || !strcmp(argv[1], "oem");
    GError *error = NULL;
    GAsyncResult *result;
    QrtrBus *bus = NULL;
    QmiDevice *device = NULL;
    QmiClient *client = NULL;
    gboolean opened = FALSE, success = FALSE, attempted_start = FALSE, start_ack = FALSE;
    gboolean stop_ack = FALSE, released = FALSE, closed = FALSE;
    gulong handler = 0;
    guint8 session = 244;
    guint32 operation_mode = G_MAXUINT32, nmea = G_MAXUINT32, revision = G_MAXUINT32;
    loop = g_main_loop_new(NULL, FALSE);
    began = g_get_monotonic_time();
    guint sigterm = g_unix_signal_add(SIGTERM, interrupted_cb, NULL);
    guint sigint = g_unix_signal_add(SIGINT, interrupted_cb, NULL);
    setvbuf(stdout, NULL, _IOLBF, 0);
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
    cid = qmi_client_get_cid(client);
    handler = g_signal_connect(device, QMI_DEVICE_SIGNAL_INDICATION, G_CALLBACK(indication), NULL);
    if (!command(device, request_new(client, 0x004b), TRUE, &operation_mode)) goto cleanup;
    if (!command(device, request_new(client, 0x0032), TRUE, &revision)) goto cleanup;
    if (!command(device, request_new(client, 0x003f), TRUE, &nmea)) goto cleanup;
    /* GET criteria may be unsupported or incomplete. Never infer LOW from absence. */
    (void)command(device, request_new(client, 0x0033), TRUE, NULL);
    QmiMessage *protocol_query = request_new(client, 0x0055);
    guint64 protocol_mask = GUINT64_TO_LE(0x60c); /* SUPL/LPP/LPPe UP+CP */
    add_bytes(protocol_query, 1, (const guint8 *)&protocol_mask, 8);
    (void)command(device, protocol_query, TRUE, NULL);
    (void)command(device, request_new(client, 0x00a9), TRUE, NULL);
    if (interrupted || ambiguous_query) goto cleanup;
    if (probe) { success = TRUE; goto cleanup; }
    if (operation_mode != QMI_LOC_OPERATION_MODE_STANDALONE || nmea == G_MAXUINT32) goto cleanup;
    QmiMessage *request = request_new(client, 0x00ba);
    add_u32(request, 1, 0xbaabcdef);
    if (!command(device, request, TRUE, NULL) || interrupted) goto cleanup;
    request = request_new(client, 0x0088);
    guint64 report_mask = GUINT64_TO_LE(0x3f), no_poly = 0;
    add_bytes(request, 16, (const guint8 *)&report_mask, 8);
    add_bytes(request, 17, (const guint8 *)&no_poly, 8);
    if (!command(device, request, TRUE, NULL) || interrupted) goto cleanup;
    request = request_new(client, 0x00d0);
    add_u32(request, 1, 2);
    gboolean resume_supported = command(device, request, TRUE, NULL);
    printf("{\"kind\":\"resume_result\",\"applied\":%s}\n", resume_supported ? "true" : "false");
    if (interrupted || ambiguous_query) goto cleanup;
    request = request_new(client, 0x0021);
    guint64 mask = GUINT64_TO_LE(0x01000187);
    add_bytes(request, 1, (const guint8 *)&mask, sizeof(mask));
    const guint8 client_id[] = {'L','A','P','I'};
    const guint8 notify = 0;
    add_bytes(request, 16, client_id, sizeof(client_id));
    add_u32(request, 17, 1);
    add_bytes(request, 18, &notify, 1);
    if (!command(device, request, FALSE, NULL) || interrupted) goto cleanup;
    request = request_new(client, 0x0022);
    add_bytes(request, 1, &session, 1);
    add_u32(request, 16, 1);
    if (high) add_u32(request, 17, 3);
    add_u32(request, 18, 2);
    add_u32(request, 19, 1000);
    attempted_start = TRUE;
    start_ack = command(device, request, FALSE, NULL);
    if (!start_ack || interrupted) goto cleanup;
    (void)command(device, request_new(client, 0x0033), TRUE, NULL);
    if (interrupted || ambiguous_query) goto cleanup;
    printf("{\"kind\":\"phase\",\"name\":\"afw-master-before-start\",\"applied\":true,\"elapsed_us\":%" G_GINT64_FORMAT "}\n", g_get_monotonic_time()-began);
    pump(90);
    request = request_new(client, 0x0088);
    add_bytes(request, 16, (const guint8 *)&no_poly, 8);
    add_bytes(request, 17, (const guint8 *)&no_poly, 8);
    gboolean report_cleared = command(device, request, TRUE, NULL);
    printf("{\"kind\":\"report_cleanup\",\"cleared\":%s}\n", report_cleared ? "true" : "false");
    success = !interrupted && !ambiguous_query;
cleanup:
    if (error) { g_printerr("LOC lifecycle: %s\n", error->message); g_clear_error(&error); }
    if (attempted_start && client) {
        QmiMessage *request = request_new(client, 0x0023);
        add_bytes(request, 1, &session, 1);
        stop_ack = command(device, request, FALSE, NULL);
        pump(2);
        (void)command(device, request_new(client, 0x0033), TRUE, NULL);
    }
    if (handler) g_signal_handler_disconnect(device, handler);
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
    printf("{\"kind\":\"cleanup\",\"probe\":%s,\"success\":%s,\"start_attempted\":%s,\"start_ack\":%s,"
           "\"stop_ack\":%s,\"client_released\":%s,\"device_closed\":%s,\"interrupted\":%s,"
           "\"operation_mode\":%u,\"nmea_mask\":%u,\"service_revision\":%u,\"elapsed_us\":%" G_GINT64_FORMAT "}\n",
           probe ? "true" : "false", success ? "true" : "false", attempted_start ? "true" : "false",
           start_ack ? "true" : "false", stop_ack ? "true" : "false", released ? "true" : "false",
           closed ? "true" : "false", interrupted ? "true" : "false", operation_mode, nmea, revision,
           g_get_monotonic_time() - began);
    g_clear_pointer(&pending_indication, qmi_message_unref);
    g_clear_object(&device); g_clear_object(&bus);
    g_source_remove(sigterm); g_source_remove(sigint); g_main_loop_unref(loop);
    return success && released && closed && (probe || stop_ack) ? 0 : 1;
}
