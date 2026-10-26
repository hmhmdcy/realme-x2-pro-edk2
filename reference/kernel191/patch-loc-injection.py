from pathlib import Path
import difflib,hashlib,json
ref=Path(__file__).resolve().parent;out=Path('/mnt/e/edk2-samurai-out/kernel191/source');out.mkdir(exist_ok=True)
original=Path('/mnt/e/edk2-samurai-out/kernel190/mm-build/ModemManager-7f0bf17ab518cd78925cf7e53cc0d5c42f88b41a/src/mm-shared-qmi.c').read_text()
assert hashlib.sha256(original.encode()).hexdigest()=='a9e6c2765e07683bf84e1876d5ecb1cba64e71db25cbe561816c56ff4efabdfa'
if (out/'mm-shared-qmi.c').exists():
 assert hashlib.sha256((out/'mm-shared-qmi.c').read_bytes()).hexdigest()==json.loads((ref/'source-patch-validation.json').read_text())['patched_source_sha256']
if (out/'mm-shared-qmi-before.c').exists():assert (out/'mm-shared-qmi-before.c').read_text()==original
else:(out/'mm-shared-qmi-before.c').write_text(original)
text=original
def replace_in_section(section,old,new):
 assert section.count(old)==1,old[:100]
 return section.replace(old,new)
def function_replace(section,name,new):
 start=section.index('static void\n'+name+' (')
 end=section.index('\nstatic ',start+1)
 return section[:start]+new.rstrip()+'\n'+section[end:]

for kind,ctype,api,ind in [('time','InjectTimeContext','inject_utc_time','InjectUtcTime'),('position','InjectPositionContext','inject_position','InjectPosition')]:
 marker='/* Location: Inject UTC time */' if kind=='time' else '/* Location: Inject position */'
 start=text.index('typedef struct {',text.index(marker))
 end=text.index('/*****************************************************************************/',start) if kind=='time' else text.index('static void\nloc_register_event_inject_req_ready (',start)
 section=text[start:end]
 section=replace_in_section(section,'    QmiClientLoc *client;\n} '+ctype+';',f'''    QmiClientLoc *client;
    gboolean      response_received;
    gboolean      completed;
    QmiIndicationLoc{ind}Output *early_indication;
}} {ctype};''')
 section=replace_in_section(section,'    g_clear_object (&ctx->client);',f'''    g_clear_pointer (&ctx->early_indication, qmi_indication_loc_{api}_output_unref);
    g_clear_object (&ctx->client);''')
 section=function_replace(section,'inject_'+kind+'_finish_task',f'''static void
inject_{kind}_finish_task (GTask  *task,
                          GError *error)
{{
    {ctype} *ctx;

    ctx = g_task_get_task_data (task);
    if (ctx->completed) {{
        g_clear_error (&error);
        return;
    }}
    ctx->completed = TRUE;
    inject_{kind}_context_cleanup_action (ctx);
    if (error)
        g_task_return_error (task, error);
    else
        g_task_return_boolean (task, TRUE);
    g_object_unref (task); /* indication/timeout reference */
}}''')
 section=replace_in_section(section,f'''    QmiLocIndicationStatus  status;
    GError                 *error = NULL;

    if (!qmi_indication_loc_{api}_output_get_indication_status''',f'''    QmiLocIndicationStatus  status;
    GError                 *error = NULL;
    {ctype} *ctx;

    ctx = g_task_get_task_data (task);
    if (ctx->completed)
        return;
    if (!ctx->response_received) {{
        if (!ctx->early_indication)
            ctx->early_indication = qmi_indication_loc_{api}_output_ref (output);
        return;
    }}

    if (!qmi_indication_loc_{api}_output_get_indication_status''')
 section=function_replace(section,'loc_location_inject_'+kind+'_ready',f'''static void
loc_location_inject_{kind}_ready (QmiClientLoc *client,
                                  GAsyncResult *res,
                                  GTask        *_task)
{{
    g_autoptr(GTask) task = _task;
    g_autoptr(QmiMessageLoc{ind}Output) output = NULL;
    {ctype} *ctx;
    GError *error = NULL;

    ctx = g_task_get_task_data (task);
    output = qmi_client_loc_{api}_finish (client, res, &error);
    if (ctx->completed) {{
        g_clear_error (&error);
        return;
    }}
    if (!output)
        g_prefix_error (&error, "QMI operation failed: ");
    else
        qmi_message_loc_{api}_output_get_result (output, &error);
    if (error) {{
        inject_{kind}_finish_task (task, error);
        return;
    }}

    ctx->response_received = TRUE;
    if (ctx->early_indication) {{
        QmiIndicationLoc{ind}Output *indication;

        indication = g_steal_pointer (&ctx->early_indication);
        loc_location_inject_{kind}_indication_cb (client, indication, task);
        qmi_indication_loc_{api}_output_unref (indication);
    }}
}}''')
 section=replace_in_section(section,f'''        (GAsyncReadyCallback)loc_location_inject_{kind}_ready,
        task);''',f'''        (GAsyncReadyCallback)loc_location_inject_{kind}_ready,
        g_object_ref (task));''')
 text=text[:start]+section+text[end:]

start=text.index('#define MAX_BYTES_PER_REQUEST 1024');end=text.index('/*****************************************************************************/',start)
section=text[start:end]
section=replace_in_section(section,'    gulong        n_part;\n} InjectAssistanceDataContext;', '''    gulong        n_part;
    gboolean      response_received;
    gboolean      completed;
    QmiIndicationLocInjectPredictedOrbitsDataOutput *early_predicted_orbits_indication;
    QmiIndicationLocInjectXtraDataOutput *early_xtra_indication;
} InjectAssistanceDataContext;''')
old_start=section.index('static void\ninject_assistance_data_context_free (');old_end=section.index('\ngboolean\n',old_start)
section=section[:old_start]+'''static void
inject_assistance_data_context_cleanup_action (InjectAssistanceDataContext *ctx)
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
inject_assistance_data_context_free (InjectAssistanceDataContext *ctx)
{
    inject_assistance_data_context_cleanup_action (ctx);
    g_clear_pointer (&ctx->early_predicted_orbits_indication, qmi_indication_loc_inject_predicted_orbits_data_output_unref);
    g_clear_pointer (&ctx->early_xtra_indication, qmi_indication_loc_inject_xtra_data_output_unref);
    g_clear_object (&ctx->client);
    g_free (ctx->data);
    g_slice_free (InjectAssistanceDataContext, ctx);
}
''' +section[old_end:]
section=replace_in_section(section,'''    ctx->timeout_id = 0;

    g_task_return_new_error''','''    ctx->timeout_id = 0;
    ctx->completed = TRUE;
    inject_assistance_data_context_cleanup_action (ctx);

    g_task_return_new_error''')
for kind,ind,nextfn,signal in [('xtra','InjectXtraData','inject_xtra_data_next','inject-xtra-data'),('predicted_orbits','InjectPredictedOrbitsData','inject_assistance_data_next','inject-predicted-orbits-data')]:
 api='inject_'+kind+'_data';field='early_'+kind+'_indication';cb='loc_location_'+api+'_indication_cb';ready=api+'_ready'
 section=replace_in_section(section,f'''    if (!qmi_indication_loc_{api}_output_get_indication_status''',f'''    ctx = g_task_get_task_data (task);
    if (ctx->completed)
        return;
    if (!ctx->response_received) {{
        if (!ctx->{field})
            ctx->{field} = qmi_indication_loc_{api}_output_ref (output);
        return;
    }}
    inject_assistance_data_context_cleanup_action (ctx);

    if (!qmi_indication_loc_{api}_output_get_indication_status''')
 cbstart=section.index('static void\n'+cb+' (');cbend=section.index('\nstatic void\n',cbstart+1)
 cbsection=section[cbstart:cbend]
 cbsection=replace_in_section(cbsection,'''    if (error) {
        g_task_return_error''','''    if (error) {
        ctx->completed = TRUE;
        g_task_return_error''')
 tailstart=cbsection.index('    ctx = g_task_get_task_data (task);',cbsection.index('out:'))
 tailend=cbsection.index('    '+nextfn+' (task);',tailstart)
 cbsection=cbsection[:tailstart]+cbsection[tailend:]
 section=section[:cbstart]+cbsection+section[cbend:]
 fallback=''
 if kind=='predicted_orbits':
  fallback='''        if (g_error_matches (error, QMI_PROTOCOL_ERROR, QMI_PROTOCOL_ERROR_NOT_SUPPORTED)) {
            inject_assistance_data_context_cleanup_action (ctx);
            g_clear_pointer (&ctx->early_predicted_orbits_indication, qmi_indication_loc_inject_predicted_orbits_data_output_unref);
            g_clear_error (&error);
            inject_xtra_data (task);
            return;
        }
'''
 section=function_replace(section,ready,f'''static void
{ready} (QmiClientLoc *client,
                         GAsyncResult *res,
                         GTask        *_task)
{{
    g_autoptr(GTask) task = _task;
    g_autoptr(QmiMessageLoc{ind}Output) output = NULL;
    InjectAssistanceDataContext *ctx;
    GError *error = NULL;

    ctx = g_task_get_task_data (task);
    output = qmi_client_loc_{api}_finish (client, res, &error);
    if (ctx->completed) {{
        g_clear_error (&error);
        return;
    }}
    if (!output)
        g_prefix_error (&error, "QMI operation failed: ");
    else
        qmi_message_loc_{api}_output_get_result (output, &error);
    if (error) {{
{fallback}        ctx->completed = TRUE;
        inject_assistance_data_context_cleanup_action (ctx);
        g_task_return_error (task, error);
        g_object_unref (task); /* indication/timeout reference */
        return;
    }}

    ctx->response_received = TRUE;
    if (ctx->{field}) {{
        QmiIndicationLoc{ind}Output *indication;

        indication = g_steal_pointer (&ctx->{field});
        {cb} (client, indication, task);
        qmi_indication_loc_{api}_output_unref (indication);
    }}
}}''')
 sendstart=section.index('static void\n'+nextfn+' (');sendend=section.index('\nstatic void',sendstart+1) if kind=='xtra' else section.index('\nvoid\nmm_shared_qmi_location_inject_assistance_data',sendstart)
 send=section[sendstart:sendend]
 send=replace_in_section(send,'''    if (total_bytes_left == 0) {
        g_task_return_boolean''','''    if (total_bytes_left == 0) {
        ctx->completed = TRUE;
        g_task_return_boolean''')
 send=replace_in_section(send,'    ctx->n_part++;',f'''    ctx->response_received = FALSE;
    /* Each part must have both a successful response and completion before
     * advancing. Keep command and indication/timeout references separate. */
    ctx->indication_id = g_signal_connect (ctx->client,
                                           "{signal}",
                                           G_CALLBACK ({cb}),
                                           task);
    ctx->timeout_id = g_timeout_add_seconds (10,
                                             (GSourceFunc)loc_location_inject_data_indication_timed_out,
                                             task);
    ctx->n_part++;''')
 # Restrict replacement to the request callback's final argument.
 old='(GAsyncReadyCallback) '+ready+',';pos=send.index(old);tail=send[pos:]
 assert tail.count('task);')==1
 send=send[:pos]+tail.replace('task);','g_object_ref (task));',1)
 section=section[:sendstart]+send+section[sendend:]
for api in ['inject_xtra_data','inject_predicted_orbits_data']:
 cbstart=section.index('static void\nloc_location_'+api+'_indication_cb (');cbend=section.index('\nstatic void',cbstart+1)
 cb=section[cbstart:cbend]
 cb=replace_in_section(cb,'    GError                      *error = NULL;', '    GError                      *error = NULL;\n    guint16                      part_number;')
 cb=replace_in_section(cb,'    if (!ctx->response_received) {',f'''    /* Ignore a stale or unrelated part when the modem identifies it. Some
     * firmware omits this optional TLV, so retain status-only compatibility. */
    if (qmi_indication_loc_{api}_output_get_part_number (output, &part_number, NULL) &&
        part_number != ctx->n_part)
        return;
    if (!ctx->response_received) {{''')
 section=section[:cbstart]+cb+section[cbend:]
text=text[:start]+section+text[end:]
(out/'mm-shared-qmi.c').write_text(text)
patch=''.join(difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile='a/src/mm-shared-qmi.c',tofile='b/src/mm-shared-qmi.c'))
(ref/'modemmanager-loc-injection-order.patch').write_text(patch)
report=dict(stage=191,base_source_sha256=hashlib.sha256(original.encode()).hexdigest(),patched_source_sha256=hashlib.sha256(text.encode()).hexdigest(),patch_sha256=hashlib.sha256(patch.encode()).hexdigest(),operations=['UTC','position','predicted-orbits','XTRA fallback'])
(ref/'source-patch-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
