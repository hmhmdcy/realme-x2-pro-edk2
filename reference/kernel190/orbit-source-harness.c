/* The production callbacks are inserted at BUILD_PRODUCTION_CALLBACKS. */
#include <gio/gio.h>
#include <stdio.h>
typedef GObject QmiClientLoc;
typedef GObject QmiClient;
typedef GObject MMSharedQmi;
typedef GObject MMIfaceModemLocation;
typedef int MMModemLocationAssistanceDataType;
typedef int QmiLocIndicationStatus;
typedef struct { int refs, kind; } Output;
typedef Output QmiMessageLocGetPredictedOrbitsDataSourceOutput;
typedef Output QmiIndicationLocGetPredictedOrbitsDataSourceOutput;
typedef Output QmiMessageLocRegisterEventsInput;
typedef struct { gchar **loc_assistance_data_servers; guint32 loc_assistance_data_max_file_size,loc_assistance_data_max_part_size; } Private;
#define MM_CORE_ERROR G_IO_ERROR
#define MM_CORE_ERROR_ABORTED G_IO_ERROR_TIMED_OUT
#define MM_MODEM_LOCATION_ASSISTANCE_DATA_TYPE_NONE 0
#define MM_MODEM_LOCATION_ASSISTANCE_DATA_TYPE_XTRA 1
#define MM_SHARED_QMI(x) ((MMSharedQmi *)(x))
#define QMI_CLIENT_LOC(x) ((QmiClientLoc *)(x))
#define QMI_SERVICE_LOC 1
#define MM_PORT_QMI_FLAG_DEFAULT 0
#define QMI_LOC_EVENT_REGISTRATION_FLAG_INJECT_TIME_REQUEST 1
#define QMI_LOC_EVENT_REGISTRATION_FLAG_INJECT_POSITION_REQUEST 2
static Private priv;
static GObject *loc;
static GTask *active;
static GAsyncReadyCallback response_cb;
static gpointer response_data;
static int response_kind,live_outputs,freed,completion_count,result,registration_count;
static gboolean have_client=TRUE;
static Private *get_private(MMSharedQmi *self) { return &priv; }
static Output *output_new(int kind) { Output *p=g_new0(Output,1);p->refs=1;p->kind=kind;live_outputs++;return p; }
static void output_unref(Output *p) { if(p && !--p->refs){live_outputs--;g_free(p);} }
static Output *output_ref(Output *p) {p->refs++;return p;}
#define qmi_indication_loc_get_predicted_orbits_data_source_output_ref output_ref
#define qmi_indication_loc_get_predicted_orbits_data_source_output_unref output_unref
#define qmi_message_loc_get_predicted_orbits_data_source_output_unref output_unref
G_DEFINE_AUTOPTR_CLEANUP_FUNC(QmiMessageLocGetPredictedOrbitsDataSourceOutput,output_unref)
G_DEFINE_AUTOPTR_CLEANUP_FUNC(QmiMessageLocRegisterEventsInput,output_unref)
static gboolean fail(GError **error) {g_set_error_literal(error,G_IO_ERROR,G_IO_ERROR_FAILED,"mock failure");return FALSE;}
static gboolean mm_error_from_qmi_loc_indication_status(int status,GError **error) {return status?fail(error):TRUE;}
static gboolean qmi_indication_loc_get_predicted_orbits_data_source_output_get_indication_status(Output *out,int *status,GError **error) {if(out->kind==3)return fail(error);*status=out->kind==2;return TRUE;}
static gboolean qmi_indication_loc_get_predicted_orbits_data_source_output_get_server_list(Output *out,GArray **servers,GError **error) {
    static GArray *a;
    if(!a) {const char *server="https://example.invalid/global-orbits";a=g_array_new(FALSE,FALSE,sizeof(char *));g_array_append_val(a,server);}
    *servers=a;return out->kind==0;
}
static gboolean qmi_indication_loc_get_predicted_orbits_data_source_output_get_allowed_sizes(Output *out,guint32 *file,guint32 *part,GError **error) {if(out->kind!=4)return FALSE;*file=65536;*part=1024;return TRUE;}
static Output *qmi_client_loc_get_predicted_orbits_data_source_finish(QmiClientLoc *client,GAsyncResult *res,GError **error) {if(response_kind==2){fail(error);return NULL;}return output_new(response_kind);}
static gboolean qmi_message_loc_get_predicted_orbits_data_source_output_get_result(Output *out,GError **error) {return out->kind?fail(error):TRUE;}
static void weak_task(gpointer data,GObject *object) {freed++;active=NULL;}
static void qmi_client_loc_get_predicted_orbits_data_source(QmiClientLoc *client,void *input,int timeout,void *cancel,GAsyncReadyCallback cb,gpointer data) {
    response_cb=cb;response_data=data;active=G_TASK(data);g_object_weak_ref(G_OBJECT(active),weak_task,NULL);
}
static QmiClient *mm_shared_qmi_peek_client(MMSharedQmi *self,int service,int flags,GError **error) {return have_client?loc:NULL;}
static Output *qmi_message_loc_register_events_input_new(void) {return output_new(0);}
static gboolean qmi_message_loc_register_events_input_set_event_registration_mask(Output *input,guint64 mask,GError **error) {return TRUE;}
static void loc_register_event_inject_req_ready(QmiClientLoc *client,GAsyncResult *res,GTask *task) {g_task_return_int(task,1);g_object_unref(task);}
static void qmi_client_loc_register_events(QmiClientLoc *client,Output *input,int timeout,void *cancel,GAsyncReadyCallback cb,gpointer data) {registration_count++;cb(G_OBJECT(client),NULL,data);}

/* BUILD_PRODUCTION_CALLBACKS */

static void done(GObject *source,GAsyncResult *res,gpointer data) {
    GError *error=NULL;completion_count++;result=mm_shared_qmi_location_load_supported_assistance_data_finish((void *)source,res,&error);
    if(error){result=-1;g_error_free(error);}
}
static void drain(void) {while(g_main_context_iteration(NULL,FALSE));}
static void scenario(const char *events,int expected) {
    GObject *self=g_object_new(G_TYPE_OBJECT,NULL);
    freed=completion_count=registration_count=0;result=-9;response_cb=NULL;active=NULL;
    mm_shared_qmi_location_load_supported_assistance_data((void *)self,done,NULL);
    for(const char *p=events;*p;p++) {
        if(*p=='A'||*p=='E'||*p=='F') {
            g_assert_nonnull(response_cb);response_kind=*p=='A'?0:*p=='E'?1:2;
            GAsyncReadyCallback cb=response_cb;gpointer data=response_data;response_cb=NULL;cb(loc,NULL,data);
        } else if(*p=='T') {
            if(active) {
                LoadSupportedAssistanceDataContext *ctx=g_task_get_task_data(active);
                if(ctx->timeout_id) {g_source_remove(ctx->timeout_id);loc_location_get_predicted_orbits_data_source_indication_timed_out(active);}
            }
        } else {
            Output *out=output_new(*p=='I'?0:*p=='N'?1:*p=='J'?2:*p=='M'?3:4);
            g_signal_emit_by_name(loc,"get-predicted-orbits-data-source",out);output_unref(out);
        }
        drain();
    }
    drain();
    if(result!=expected)g_error("scenario %s expected %d got %d",events,expected,result);
    g_assert_cmpint(completion_count,==,1);g_assert_cmpint(freed,==,1);g_assert_cmpint(live_outputs,==,0);
    g_assert_false(g_signal_has_handler_pending(loc,g_signal_lookup("get-predicted-orbits-data-source",G_TYPE_OBJECT),0,TRUE));
    g_strfreev(priv.loc_assistance_data_servers);memset(&priv,0,sizeof(priv));g_object_unref(self);
}
int main(void) {
    g_log_set_always_fatal(G_LOG_LEVEL_WARNING|G_LOG_LEVEL_CRITICAL);
    g_signal_new("get-predicted-orbits-data-source",G_TYPE_OBJECT,G_SIGNAL_RUN_LAST,0,NULL,NULL,NULL,G_TYPE_NONE,1,G_TYPE_POINTER);
    loc=g_object_new(G_TYPE_OBJECT,NULL);
    struct {const char *events;int expected;} cases[]={
      {"IA",1},{"AI",1},{"IIAI",1},{"AII",1},{"NA",0},{"AN",0},{"JA",-1},{"AJ",-1},{"MA",-1},{"AM",-1},
      {"SA",1},{"AS",1},{"IEI",-1},{"IFI",-1},{"EII",-1},{"FII",-1},
      {"ITAII",-1},{"ITFII",-1},{"TAII",-1},{"TEII",-1},{"TFII",-1},{"ATII",-1},{"AITA",1}
    };
    /* AITA has no second ACK; use a timeout/duplicate indication after success. */
    cases[G_N_ELEMENTS(cases)-1].events="AITI";
    for(guint i=0;i<G_N_ELEMENTS(cases);i++)scenario(cases[i].events,cases[i].expected);
    g_object_unref(loc);printf("%u production callback ordering/lifetime cases passed\n",(unsigned)G_N_ELEMENTS(cases));return 0;
}
