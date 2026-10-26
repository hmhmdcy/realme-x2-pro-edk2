/* Real production callbacks are inserted below; QMI transport is simulated. */
#include <gio/gio.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef GObject QmiClientLoc;
typedef GObject QmiClient;
typedef GObject MMSharedQmi;
typedef GObject MMIfaceModemLocation;
typedef int QmiLocIndicationStatus;
typedef struct {int refs,kind;guint32 total_size;guint16 total_parts,part;gboolean have_part;GArray *data;} Output;
typedef struct {guint32 loc_assistance_data_max_file_size,loc_assistance_data_max_part_size;gpointer location_cache;} Private;
#define MM_SHARED_QMI(x) ((MMSharedQmi *)(x))
#define QMI_CLIENT_LOC(x) ((QmiClientLoc *)(x))
#define MM_CORE_ERROR G_IO_ERROR
#define MM_CORE_ERROR_ABORTED G_IO_ERROR_TIMED_OUT
#define MM_CORE_ERROR_TOO_MANY G_IO_ERROR_INVALID_ARGUMENT
#define QMI_PROTOCOL_ERROR G_FILE_ERROR
#define QMI_PROTOCOL_ERROR_NOT_SUPPORTED 17
#define QMI_SERVICE_LOC 1
#define QMI_LOC_INJECTED_TIME_SOURCE_UNKNOWN 0
#define QMI_LOC_POSITION_SOURCE_OTHER 0
#define QMI_LOC_PREDICTED_ORBITS_DATA_FORMAT_XTRA 0
#define MM_LOCATION_LATITUDE_UNKNOWN G_MAXDOUBLE
#define MM_LOCATION_LONGITUDE_UNKNOWN G_MAXDOUBLE
#define mm_obj_dbg(...) ((void)0)
static GObject *loc;
static Private priv;
static GTask *active,*observed;
static GAsyncReadyCallback pending_cb;
static gpointer pending_data;
static int case_mode,current_op,response_kind,live_outputs,freed,completions,result,cases;
static guint16 current_part;
static guint request_count[4];
static GByteArray *sent[4];
static const guint8 *expected_data;
static gsize expected_size,expected_part;
static gboolean already_position,cached_unknown;
static const char *signals[]={"inject-utc-time","inject-position","inject-predicted-orbits-data","inject-xtra-data"};
static Private *get_private(MMSharedQmi *self) {return &priv;}
static Output *output_new(int kind) {Output *p=g_new0(Output,1);p->kind=kind;p->refs=1;live_outputs++;return p;}
static Output *output_ref(Output *p) {p->refs++;return p;}
static void output_unref(Output *p) {if(p && !--p->refs){if(p->data)g_array_unref(p->data);live_outputs--;g_free(p);}}
static gboolean fail(GError **error) {g_set_error_literal(error,G_IO_ERROR,G_IO_ERROR_FAILED,"mock failure");return FALSE;}
static gboolean mm_error_from_qmi_loc_indication_status(int status,GError **error) {return status?fail(error):TRUE;}
static gboolean indication_status(Output *p,int *status,GError **error) {if(p->kind==5)return fail(error);*status=p->kind==4;return TRUE;}
static gboolean indication_part(Output *p,guint16 *part,GError **error) {*part=p->part;return p->have_part;}
static Output *fake_finish(QmiClientLoc *client,GAsyncResult *res,GError **error) {if(response_kind==2){fail(error);return NULL;}return output_new(response_kind);}
static gboolean response_result(Output *p,GError **error) {
 if(p->kind==3){g_set_error_literal(error,QMI_PROTOCOL_ERROR,QMI_PROTOCOL_ERROR_NOT_SUPPORTED,"unsupported");return FALSE;}
 return p->kind?fail(error):TRUE;
}
static gboolean set_total(Output *p,guint32 n,GError **error) {p->total_size=n;return TRUE;}
static gboolean set_parts(Output *p,guint16 n,GError **error) {p->total_parts=n;return TRUE;}
static gboolean set_part(Output *p,guint16 n,GError **error) {p->part=n;return TRUE;}
static gboolean set_data(Output *p,GArray *data,GError **error) {p->data=g_array_ref(data);return TRUE;}
static gboolean set_utc(Output *p,guint64 value,GError **error) {g_assert_cmpuint(value,>,0);return TRUE;}
static gboolean set_uncertainty(Output *p,guint32 value,GError **error) {g_assert_cmpuint(value,==,1000);return TRUE;}
static gboolean get_lat(Output *p,gdouble *value,GError **error) {*value=already_position?1.0:0.0;return TRUE;}
static gboolean get_lon(Output *p,gdouble *value,GError **error) {*value=already_position?2.0:0.0;return TRUE;}
static gboolean get_time(Output *p,guint64 *value,GError **error) {*value=already_position?1000:0;return TRUE;}
static void mm_location_cache_get_lat_lon(gpointer cache,gdouble *lat,gdouble *lon) {*lat=cached_unknown?G_MAXDOUBLE:1.25;*lon=cached_unknown?G_MAXDOUBLE:2.5;}
static gboolean mm_shared_qmi_ensure_client(MMSharedQmi *self,int service,QmiClient **client,GAsyncReadyCallback cb,gpointer user) {*client=loc;return TRUE;}
static void weak_task(gpointer data,GObject *object) {freed++;active=NULL;}
static void completed(GObject *object,GParamSpec *pspec,gpointer data) {
 if(g_task_get_completed(G_TASK(object))){GError *error=NULL;completions++;result=g_task_propagate_boolean(G_TASK(object),&error)?1:-1;g_clear_error(&error);}
}
static void fake_send(int op,QmiClientLoc *client,Output *input,int timeout,void *cancel,GAsyncReadyCallback cb,gpointer data) {
 g_assert_null(pending_cb);pending_cb=cb;pending_data=data;current_op=op;active=G_TASK(data);request_count[op]++;
 if(!observed){observed=active;g_object_weak_ref(G_OBJECT(active),weak_task,NULL);if(case_mode<2)g_signal_connect(active,"notify::completed",G_CALLBACK(completed),NULL);}
 g_assert_true(active==observed);
 if(op>=2){
  current_part=input->part;g_assert_cmpuint(input->total_size,==,expected_size);g_assert_cmpuint(input->part,==,request_count[op]);
  g_assert_cmpuint(input->total_parts,==,(expected_size+expected_part-1)/expected_part);
  gsize offset=(input->part-1)*expected_part,count=MIN(expected_part,expected_size-offset);
  g_assert_nonnull(input->data);g_assert_cmpuint(input->data->len,==,count);g_assert_cmpmem(input->data->data,count,expected_data+offset,count);
  g_byte_array_append(sent[op],(guint8 *)input->data->data,count);
 }
}

/* BUILD_API_MOCKS */

/* BUILD_PRODUCTION_CALLBACKS */

static void done(GObject *self,GAsyncResult *res,gpointer data) {
 GError *error=NULL;completions++;result=mm_shared_qmi_location_inject_assistance_data_finish((void *)self,res,&error)?1:-1;g_clear_error(&error);
}
static void drain(void) {while(g_main_context_iteration(NULL,FALSE));}
static void event(char e) {
 if(strchr("AEFU",e)){
  g_assert_nonnull(pending_cb);response_kind=e=='A'?0:e=='E'?1:e=='F'?2:3;
  GAsyncReadyCallback cb=pending_cb;gpointer data=pending_data;pending_cb=NULL;pending_data=NULL;cb(loc,NULL,data);
 }else if(e=='T'){
  if(active){guint id=case_mode==0?((InjectTimeContext *)g_task_get_task_data(active))->timeout_id:case_mode==1?((InjectPositionContext *)g_task_get_task_data(active))->timeout_id:((InjectAssistanceDataContext *)g_task_get_task_data(active))->timeout_id;
   if(id){GSource *source=g_main_context_find_source_by_id(NULL,id);g_assert_nonnull(source);g_source_set_ready_time(source,0);}
  }
 }else{
  Output *p=output_new(e=='J'?4:e=='M'?5:0);p->have_part=e!='N';p->part=current_part;
  if(e=='D')p->part=current_part?current_part-1:0;
  if(e=='K')p->part=current_part+1;
  g_signal_emit_by_name(loc,signals[e=='P'?2:current_op],p);output_unref(p);
 }
 drain();
}
static GObject *begin(int mode,gsize size,guint32 part,guint32 max_file) {
 GObject *self=g_object_new(G_TYPE_OBJECT,NULL);case_mode=mode;current_op=mode<2?mode:2;current_part=0;
 freed=completions=0;result=-9;pending_cb=NULL;pending_data=NULL;active=observed=NULL;memset(request_count,0,sizeof(request_count));
 priv.loc_assistance_data_max_file_size=max_file;priv.loc_assistance_data_max_part_size=part;priv.location_cache=&priv;
 for(int i=0;i<4;i++)sent[i]=g_byte_array_new();
 if(mode==0)loc_location_inject_time_req_indication_cb(loc,NULL,(void *)self);
 else if(mode==1)loc_location_inject_position_req_indication_cb(loc,NULL,(void *)self);
 else{
  guint8 *data=g_malloc(MAX((gsize)1,size));for(gsize i=0;i<size;i++)data[i]=(i*37+11)%251;
  expected_data=data;expected_size=size;expected_part=part?part:1024;
  mm_shared_qmi_location_inject_assistance_data((void *)self,data,size,done,NULL);
 }
 drain();return self;
}
static void finish(GObject *self,int expected,gboolean expect_weak) {
 drain();g_assert_cmpint(result,==,expected);g_assert_cmpint(completions,==,1);g_assert_cmpint(freed,==,expect_weak?1:0);
 g_assert_null(pending_cb);g_assert_null(active);g_assert_cmpint(live_outputs,==,0);
 for(int i=0;i<4;i++){g_assert_false(g_signal_has_handler_pending(loc,g_signal_lookup(signals[i],G_TYPE_OBJECT),0,TRUE));g_byte_array_unref(sent[i]);}
 if(case_mode>=2){g_free((void *)expected_data);expected_data=NULL;}
 g_object_unref(self);cases++;
}
static void single(int mode,const char *events,int expected) {
 GObject *self=begin(mode,17,0,0);if(mode==3)event('U');
 for(const char *p=events;*p;p++)event(*p);
 finish(self,expected,TRUE);
}
static void multipart(int mode,gsize size,guint32 part,const char *pattern,gboolean early_fallback) {
 GObject *self=begin(mode,size,part,0);
 if(mode==3){if(early_fallback)event('I');event('U');event('P');}
 guint parts=(size+expected_part-1)/expected_part;
 for(guint i=0;i<parts;i++)for(const char *p=pattern;*p;p++)event(*p);
 g_assert_cmpmem(sent[mode==3?3:2]->data,sent[mode==3?3:2]->len,expected_data,size);
 g_assert_cmpuint(request_count[mode==3?3:2],==,parts);
 finish(self,1,TRUE);
}
static void mismatched_parts(int mode) {
 GObject *self=begin(mode,2500,0,0);if(mode==3)event('U');
 int op=mode==3?3:2;
 for(guint part=1;part<=3;part++){
  event('K');event('D');event('A');
  /* An ACK plus an indication for another part must not advance the wire
   * protocol, even if all payload bytes would eventually be sent anyway. */
  g_assert_cmpuint(request_count[op],==,part);g_assert_cmpint(completions,==,0);
  event('K');event('D');g_assert_cmpuint(request_count[op],==,part);g_assert_cmpint(completions,==,0);
  event('I');g_assert_cmpuint(request_count[op],==,MIN(part+1,3));
 }
 finish(self,1,TRUE);
}
int main(int argc,char **argv) {
 g_log_set_always_fatal(G_LOG_LEVEL_WARNING|G_LOG_LEVEL_CRITICAL);
 for(int i=0;i<4;i++)g_signal_new(signals[i],G_TYPE_OBJECT,G_SIGNAL_RUN_LAST,0,NULL,NULL,NULL,G_TYPE_NONE,1,G_TYPE_POINTER);
 loc=g_object_new(G_TYPE_OBJECT,NULL);
 if(argc==5){single(atoi(argv[1]),argv[2],atoi(argv[3]));g_object_unref(loc);return 0;}
 struct {const char *events;int expected;} tests[]={
  {"AI",1},{"IA",1},{"IIA",1},{"AII",1},{"IE",-1},{"IF",-1},{"TA",-1},{"TE",-1},{"TF",-1},
  {"ITA",-1},{"ITE",-1},{"ITF",-1},{"ATI",-1},{"ATJ",-1},{"JA",-1},{"AJ",-1},{"MA",-1},{"AM",-1}};
 for(int mode=0;mode<4;mode++)for(guint i=0;i<G_N_ELEMENTS(tests);i++)single(mode,tests[i].events,tests[i].expected);
 const gsize sizes[]={1,1024,1025,2500,50413};const guint32 parts[]={0,257,4096};const char *patterns[]={"AI","IA","IIA","AID","KIA","NA"};
 for(int mode=2;mode<4;mode++)for(guint s=0;s<G_N_ELEMENTS(sizes);s++)for(guint p=0;p<G_N_ELEMENTS(parts);p++)for(guint o=0;o<G_N_ELEMENTS(patterns);o++)multipart(mode,sizes[s],parts[p],patterns[o],TRUE);
 mismatched_parts(2);mismatched_parts(3);
 GObject *self=begin(2,17,0,16);finish(self,-1,FALSE);
 self=begin(2,65536,1,0);finish(self,-1,FALSE);
 self=begin(2,0,0,0);finish(self,1,FALSE);
 g_object_unref(loc);printf("%d production callback and real chunk-construction cases passed\n",cases);return 0;
}
