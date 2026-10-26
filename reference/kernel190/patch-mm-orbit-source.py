"""Fix early LOC indications in the pinned ModemManager source."""
from pathlib import Path
import difflib,hashlib,json

ref=Path(__file__).resolve().parent
root=Path('/mnt/e/edk2-samurai-out/kernel190/mm-build/ModemManager-7f0bf17ab518cd78925cf7e53cc0d5c42f88b41a')
path=root/'src/mm-shared-qmi.c'
original=Path('/mnt/e/edk2-samurai-out/kernel190/location-sources/src/mm-shared-qmi.c').read_text()
assert path.read_text()==original,'apply only to the pinned unmodified source'
text=original
def replace(old,new):
    global text
    assert text.count(old)==1,old[:100]
    text=text.replace(old,new)

replace('''    guint         timeout_id;
} LoadSupportedAssistanceDataContext;''','''    guint         timeout_id;
    gboolean      response_received;
    gboolean      completed;
    QmiIndicationLocGetPredictedOrbitsDataSourceOutput *early_indication;
} LoadSupportedAssistanceDataContext;''')
replace('''static void
load_supported_assistance_data_context_free (LoadSupportedAssistanceDataContext *ctx)
{
    if (ctx->client) {
        if (ctx->timeout_id)
            g_source_remove (ctx->timeout_id);
        if (ctx->indication_id)
            g_signal_handler_disconnect (ctx->client, ctx->indication_id);
        g_object_unref (ctx->client);
    }
    g_slice_free (LoadSupportedAssistanceDataContext, ctx);
}''','''static void
load_supported_assistance_data_context_cleanup_action (LoadSupportedAssistanceDataContext *ctx)
{
    if (ctx->timeout_id) {
        g_source_remove (ctx->timeout_id);
        ctx->timeout_id = 0;
    }
    if (ctx->indication_id) {
        g_signal_handler_disconnect (ctx->client, ctx->indication_id);
        ctx->indication_id = 0;
    }
}

static void
load_supported_assistance_data_context_free (LoadSupportedAssistanceDataContext *ctx)
{
    load_supported_assistance_data_context_cleanup_action (ctx);
    g_clear_pointer (&ctx->early_indication, qmi_indication_loc_get_predicted_orbits_data_source_output_unref);
    g_clear_object (&ctx->client);
    g_slice_free (LoadSupportedAssistanceDataContext, ctx);
}''')
replace('''    ctx->timeout_id = 0;

    g_task_return_new_error (task, MM_CORE_ERROR, MM_CORE_ERROR_ABORTED,
                             "Failed to receive indication with the predicted orbits data source");''','''    ctx->timeout_id = 0;
    ctx->completed = TRUE;
    load_supported_assistance_data_context_cleanup_action (ctx);

    g_task_return_new_error (task, MM_CORE_ERROR, MM_CORE_ERROR_ABORTED,
                             "Failed to receive indication with the predicted orbits data source");''')
replace('''    gboolean                supported = FALSE;

    if (!qmi_indication_loc_get_predicted_orbits_data_source_output_get_indication_status''','''    gboolean                supported = FALSE;
    LoadSupportedAssistanceDataContext *ctx;

    ctx = g_task_get_task_data (task);
    if (ctx->completed)
        return;
    /* LOC may emit completion before the command response. Keep the boxed
     * output until that response has been checked. */
    if (!ctx->response_received) {
        if (!ctx->early_indication)
            ctx->early_indication = qmi_indication_loc_get_predicted_orbits_data_source_output_ref (output);
        return;
    }
    ctx->completed = TRUE;
    load_supported_assistance_data_context_cleanup_action (ctx);

    if (!qmi_indication_loc_get_predicted_orbits_data_source_output_get_indication_status''')
start=text.index('static void\nloc_location_get_predicted_orbits_data_source_ready (')
end=text.index('\nvoid\nmm_shared_qmi_location_load_supported_assistance_data (',start)
text=text[:start]+'''static void
loc_location_get_predicted_orbits_data_source_ready (QmiClientLoc *client,
                                                     GAsyncResult *res,
                                                     GTask        *_task)
{
    g_autoptr(GTask) task = _task;
    g_autoptr(QmiMessageLocGetPredictedOrbitsDataSourceOutput) output = NULL;
    LoadSupportedAssistanceDataContext *ctx;
    GError *error = NULL;

    ctx = g_task_get_task_data (task);
    output = qmi_client_loc_get_predicted_orbits_data_source_finish (client, res, &error);
    /* The indication timeout may already have completed the task. The command
     * callback owns a separate reference, so even a late reply is safe. */
    if (ctx->completed) {
        g_clear_error (&error);
        return;
    }
    if (!output)
        g_prefix_error (&error, "QMI operation failed: ");
    else
        qmi_message_loc_get_predicted_orbits_data_source_output_get_result (output, &error);
    if (error) {
        ctx->completed = TRUE;
        load_supported_assistance_data_context_cleanup_action (ctx);
        g_task_return_error (task, error);
        g_object_unref (task); /* indication/timeout reference */
        return;
    }

    ctx->response_received = TRUE;
    if (ctx->early_indication) {
        QmiIndicationLocGetPredictedOrbitsDataSourceOutput *indication;

        indication = g_steal_pointer (&ctx->early_indication);
        loc_location_get_predicted_orbits_data_source_indication_cb (client, indication, task);
        qmi_indication_loc_get_predicted_orbits_data_source_output_unref (indication);
    }
}
''' +text[end:]
replace('''    qmi_client_loc_get_predicted_orbits_data_source (ctx->client,
                                                     NULL,
                                                     10,
                                                     NULL,
                                                     (GAsyncReadyCallback)loc_location_get_predicted_orbits_data_source_ready,
                                                     task);''','''    /* Listen before sending: some modems send the completion before the ACK.
     * The initial reference belongs to the indication/timeout pair. */
    ctx->indication_id = g_signal_connect (ctx->client,
                                           "get-predicted-orbits-data-source",
                                           G_CALLBACK (loc_location_get_predicted_orbits_data_source_indication_cb),
                                           task);
    ctx->timeout_id = g_timeout_add_seconds (10,
                                             (GSourceFunc)loc_location_get_predicted_orbits_data_source_indication_timed_out,
                                             task);
    qmi_client_loc_get_predicted_orbits_data_source (ctx->client,
                                                     NULL,
                                                     10,
                                                     NULL,
                                                     (GAsyncReadyCallback)loc_location_get_predicted_orbits_data_source_ready,
                                                     g_object_ref (task));''')
path.write_text(text)
patch=''.join(difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile='a/src/mm-shared-qmi.c',tofile='b/src/mm-shared-qmi.c'))
(ref/'modemmanager-loc-early-orbit-source.patch').write_text(patch)
(ref/'mm-patch-validation.json').write_text(json.dumps(dict(original_sha256=hashlib.sha256(original.encode()).hexdigest(),patched_sha256=hashlib.sha256(text.encode()).hexdigest(),patch_sha256=hashlib.sha256(patch.encode()).hexdigest()),indent=2)+'\n')
print('Applied pinned LOC source race fix')
