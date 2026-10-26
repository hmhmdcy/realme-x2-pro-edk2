/* Execute the actual complete candidate manager with real GLib/GIO objects,
 * signals, weak refs, tasks and cancellation. Only UPower/D-Bus is simulated. */
#include <gio/gio.h>
#include <math.h>
#include <string.h>
#include "manager.h"
#include "upower.h"

G_DEFINE_TYPE (PhoshManager, phosh_manager, G_TYPE_OBJECT)
static void phosh_manager_class_init (PhoshManagerClass *klass) { }
static void phosh_manager_init (PhoshManager *self) { }

struct _UpDevice { GObject parent; char *path; guint kind, state; gboolean online; double percentage; };
enum { D0, DKIND, DONLINE, DSTATE, DPERCENT, DEND };
static GParamSpec *device_props[DEND];
static guint devices_freed, clients_freed;
G_DEFINE_TYPE (UpDevice, up_device, G_TYPE_OBJECT)
static void device_set (GObject *o, guint p, const GValue *v, GParamSpec *s) {
  UpDevice *d=UP_DEVICE(o);
  switch(p) {case DKIND:d->kind=g_value_get_uint(v);break;case DONLINE:d->online=g_value_get_boolean(v);break;
    case DSTATE:d->state=g_value_get_uint(v);break;case DPERCENT:d->percentage=g_value_get_double(v);break;default:g_assert_not_reached();}
}
static void device_get (GObject *o, guint p, GValue *v, GParamSpec *s) {
  UpDevice *d=UP_DEVICE(o);
  switch(p) {case DKIND:g_value_set_uint(v,d->kind);break;case DONLINE:g_value_set_boolean(v,d->online);break;
    case DSTATE:g_value_set_uint(v,d->state);break;case DPERCENT:g_value_set_double(v,d->percentage);break;default:g_assert_not_reached();}
}
static void device_finalize (GObject *o) { g_free(UP_DEVICE(o)->path);devices_freed++;G_OBJECT_CLASS(up_device_parent_class)->finalize(o); }
static void up_device_class_init (UpDeviceClass *c) {
  GObjectClass *o=G_OBJECT_CLASS(c);o->set_property=device_set;o->get_property=device_get;o->finalize=device_finalize;
  device_props[DKIND]=g_param_spec_uint("kind","","",0,8,0,G_PARAM_READWRITE);
  device_props[DONLINE]=g_param_spec_boolean("online","","",FALSE,G_PARAM_READWRITE);
  device_props[DSTATE]=g_param_spec_uint("state","","",0,8,0,G_PARAM_READWRITE);
  device_props[DPERCENT]=g_param_spec_double("percentage","","",0,100,0,G_PARAM_READWRITE);
  g_object_class_install_properties(o,DEND,device_props);
}
static void up_device_init (UpDevice *d) { }
static UpDevice *device_new (const char *path,guint kind,gboolean online) {
  UpDevice *d=g_object_new(UP_TYPE_DEVICE,"kind",kind,"online",online,"state",UP_DEVICE_STATE_DISCHARGING,"percentage",50.0,NULL);
  d->path=g_strdup(path);return d;
}
const char *up_device_get_object_path (UpDevice *d) { return d->path; }

struct _UpClient { GObject parent; UpDevice *display; };
static guint added_signal, removed_signal;
G_DEFINE_TYPE (UpClient, up_client, G_TYPE_OBJECT)
static void client_finalize (GObject *o) { g_clear_object(&UP_CLIENT(o)->display);clients_freed++;G_OBJECT_CLASS(up_client_parent_class)->finalize(o); }
static void up_client_class_init (UpClientClass *c) {
  G_OBJECT_CLASS(c)->finalize=client_finalize;
  added_signal=g_signal_new("device-added",G_TYPE_FROM_CLASS(c),G_SIGNAL_RUN_LAST,0,NULL,NULL,NULL,G_TYPE_NONE,1,UP_TYPE_DEVICE);
  removed_signal=g_signal_new("device-removed",G_TYPE_FROM_CLASS(c),G_SIGNAL_RUN_LAST,0,NULL,NULL,NULL,G_TYPE_NONE,1,G_TYPE_STRING);
}
static void up_client_init (UpClient *c) { c->display=device_new("/Display",UP_DEVICE_KIND_BATTERY,FALSE); }
UpDevice *up_client_get_display_device (UpClient *c) { return g_object_ref(c->display); }

typedef struct { GTask *task; gboolean enumeration; } Pending;
static GQueue pending=G_QUEUE_INIT;
static guint new_client_calls, enum_calls, attached_before_enumeration;
static void queue_call (GObject *source,GCancellable *cancel,GAsyncReadyCallback cb,gpointer data,gboolean enumeration) {
  Pending *p=g_new0(Pending,1);p->task=g_task_new(source,cancel,cb,data);p->enumeration=enumeration;g_queue_push_tail(&pending,p);
}
void up_client_new_async (GCancellable *cancel,GAsyncReadyCallback cb,gpointer data) {
  new_client_calls++;queue_call(NULL,cancel,cb,data,FALSE);
}
UpClient *up_client_new_finish (GAsyncResult *r,GError **e) { return g_task_propagate_pointer(G_TASK(r),e); }
void up_client_get_devices_async (UpClient *c,GCancellable *cancel,GAsyncReadyCallback cb,gpointer data) {
  enum_calls++;
  g_assert_true(g_signal_has_handler_pending(c,added_signal,0,TRUE));
  g_assert_true(g_signal_has_handler_pending(c,removed_signal,0,TRUE));attached_before_enumeration++;
  queue_call(G_OBJECT(c),cancel,cb,data,TRUE);
}
GPtrArray *up_client_get_devices_finish (UpClient *c,GAsyncResult *r,GError **e) { return g_task_propagate_pointer(G_TASK(r),e); }
static void drain (void) { while(g_main_context_iteration(NULL,FALSE)); }
static void complete_client (gboolean success) {
  Pending *p=g_queue_pop_head(&pending);g_assert_nonnull(p);g_assert_false(p->enumeration);
  if(success)g_task_return_pointer(p->task,g_object_new(UP_TYPE_CLIENT,NULL),g_object_unref);
  else g_task_return_new_error(p->task,G_IO_ERROR,G_IO_ERROR_FAILED,"synthetic client error");
  g_object_unref(p->task);g_free(p);drain();
}
static void complete_enum (gboolean success,UpDevice *a,UpDevice *b) {
  Pending *p=g_queue_pop_head(&pending);g_assert_nonnull(p);g_assert_true(p->enumeration);
  if(success) { GPtrArray *array=g_ptr_array_new_with_free_func(g_object_unref);if(a)g_ptr_array_add(array,g_object_ref(a));if(b)g_ptr_array_add(array,g_object_ref(b));
    g_task_return_pointer(p->task,array,(GDestroyNotify)g_ptr_array_unref); }
  else g_task_return_new_error(p->task,G_IO_ERROR,G_IO_ERROR_FAILED,"synthetic enumeration error");
  g_object_unref(p->task);g_free(p);drain();
}

typedef struct { guint id;GBusNameAppearedCallback appeared;GBusNameVanishedCallback vanished;gpointer data;GDestroyNotify destroy; } Watch;
static Watch watch;
static guint watch_serial,watch_starts,watch_stops;
static guint fake_bus_watch_name (GBusType type,const char *name,GBusNameWatcherFlags flags,GBusNameAppearedCallback a,GBusNameVanishedCallback v,gpointer data,GDestroyNotify destroy) {
  g_assert_cmpstr(name,==,"org.freedesktop.UPower");g_assert_cmpint(type,==,G_BUS_TYPE_SYSTEM);g_assert_cmpint(flags,==,G_BUS_NAME_WATCHER_FLAGS_AUTO_START);g_assert_cmpuint(watch.id,==,0);
  watch=(Watch){++watch_serial,a,v,data,destroy};watch_starts++;return watch.id;
}
static void fake_bus_unwatch_name (guint id) { g_assert_cmpuint(id,==,watch.id);watch.destroy(watch.data);memset(&watch,0,sizeof watch);watch_stops++; }
#define g_bus_watch_name fake_bus_watch_name
#define g_bus_unwatch_name fake_bus_unwatch_name
#undef G_LOG_DOMAIN
#include "../candidate/src/battery-manager.c"
#undef g_bus_watch_name
#undef g_bus_unwatch_name

static PhoshBatteryManager *start (void) {
  PhoshBatteryManager *m=phosh_battery_manager_new();
  PHOSH_MANAGER_GET_CLASS(m)->idle_init(PHOSH_MANAGER(m));g_assert_cmpuint(watch.id,>,0);return m;
}
static void appear (void) { watch.appeared(NULL,"org.freedesktop.UPower",":test-owner",watch.data); }
static void vanish (void) { watch.vanished(NULL,"org.freedesktop.UPower",watch.data); }
static void state (PhoshBatteryManager *m,gboolean known,gboolean connected) {
  gboolean k,c;g_object_get(m,"external-power-known",&k,"external-power-connected",&c,NULL);g_assert_cmpint(k,==,known);g_assert_cmpint(c,==,connected);
}
static void finish (PhoshBatteryManager *m) { g_object_unref(m);g_assert_cmpuint(watch.id,==,0);g_assert_true(g_queue_is_empty(&pending)); }
static void notifications (GObject *o,GParamSpec *p,guint *n) { (*n)++; }
static void dispose_on_unknown (GObject *o,GParamSpec *p,gpointer data) {
  gboolean known;g_object_get(o,"external-power-known",&known,NULL);if(!known)g_object_run_dispose(o);
}

int main (void) {
  guint cases=0;
  /* 1: Startup waits for an owner; all observers precede async enumeration. */
  PhoshBatteryManager *m=start();state(m,FALSE,FALSE);g_assert_true(g_queue_is_empty(&pending));
  appear();state(m,FALSE,FALSE);complete_client(TRUE);g_assert_cmpuint(attached_before_enumeration,==,enum_calls);
  UpDevice *line=device_new("/line",UP_DEVICE_KIND_LINE_POWER,TRUE),*off=device_new("/off",UP_DEVICE_KIND_LINE_POWER,FALSE);
  complete_enum(TRUE,line,off);state(m,TRUE,TRUE);g_assert_cmpstr(m->icon_name,==,"battery-level-50-symbolic");
  guint n=0;g_signal_connect(m,"notify::external-power-connected",G_CALLBACK(notifications),&n);
  g_object_set(line,"online",TRUE,NULL);state(m,TRUE,TRUE);g_assert_cmpuint(n,==,0);
  g_object_set(line,"online",FALSE,NULL);state(m,TRUE,FALSE);g_assert_cmpuint(n,==,1);g_assert_cmpstr(m->icon_name,==,"battery-level-50-symbolic");
  finish(m);g_object_unref(line);g_object_unref(off);cases++;
  /* 2: No line device and unknown kinds do not prove disconnected. */
  m=start();appear();complete_client(TRUE);UpDevice *u=device_new("/unknown",UP_DEVICE_KIND_UNKNOWN,FALSE);
  complete_enum(TRUE,u,NULL);state(m,FALSE,FALSE);g_object_set(u,"kind",UP_DEVICE_KIND_LINE_POWER,NULL);state(m,TRUE,FALSE);
  g_object_set(u,"online",TRUE,NULL);state(m,TRUE,TRUE);finish(m);g_object_unref(u);cases++;
  /* 3: Removed during an outstanding enumeration cannot be resurrected. */
  m=start();appear();complete_client(TRUE);line=device_new("/line",UP_DEVICE_KIND_LINE_POWER,TRUE);
  g_signal_emit(m->upower,added_signal,0,line);state(m,TRUE,TRUE);g_assert_cmpuint(g_queue_get_length(&pending),==,2);
  g_signal_emit(m->upower,removed_signal,0,"/line");state(m,FALSE,FALSE);
  complete_enum(TRUE,line,NULL);state(m,FALSE,FALSE);complete_enum(TRUE,line,NULL);state(m,FALSE,FALSE);
  complete_enum(TRUE,NULL,NULL);state(m,FALSE,FALSE);g_assert_cmpuint(g_hash_table_size(m->power_devices),==,0);
  finish(m);g_object_unref(line);cases++;
  /* 4: Duplicate paths replace references and detach the old signal source. */
  m=start();appear();complete_client(TRUE);line=device_new("/same",UP_DEVICE_KIND_LINE_POWER,TRUE);off=device_new("/same",UP_DEVICE_KIND_LINE_POWER,FALSE);
  complete_enum(TRUE,line,NULL);state(m,TRUE,TRUE);g_signal_emit(m->upower,added_signal,0,off);state(m,FALSE,FALSE);
  complete_enum(TRUE,off,NULL);state(m,TRUE,FALSE);g_assert_true(g_hash_table_lookup(m->power_devices,"/same")==off);
  g_object_set(line,"online",TRUE,NULL);state(m,TRUE,FALSE);g_assert_cmpuint(g_hash_table_size(m->power_devices),==,1);
  finish(m);g_object_unref(line);g_object_unref(off);cases++;
  /* 5: Failed enumeration is unknown; a known positive signal remains useful. */
  m=start();appear();complete_client(TRUE);complete_enum(FALSE,NULL,NULL);state(m,FALSE,FALSE);
  line=device_new("/line",UP_DEVICE_KIND_LINE_POWER,TRUE);g_signal_emit(m->upower,added_signal,0,line);state(m,TRUE,TRUE);
  complete_enum(FALSE,NULL,NULL);state(m,TRUE,TRUE);g_object_set(line,"online",FALSE,NULL);state(m,FALSE,FALSE);
  finish(m);g_object_unref(line);cases++;
  /* 6: Owner loss clears refs; old completion and old device signals are inert. */
  m=start();appear();complete_client(TRUE);line=device_new("/old",UP_DEVICE_KIND_LINE_POWER,TRUE);complete_enum(TRUE,line,NULL);state(m,TRUE,TRUE);
  UpClient *old=g_object_ref(m->upower);g_signal_emit(old,added_signal,0,line);vanish();state(m,FALSE,FALSE);
  appear();complete_enum(TRUE,line,NULL);state(m,FALSE,FALSE);complete_client(TRUE);
  off=device_new("/new",UP_DEVICE_KIND_LINE_POWER,FALSE);complete_enum(TRUE,off,NULL);state(m,TRUE,FALSE);
  g_signal_emit(old,added_signal,0,line);g_object_set(line,"online",TRUE,NULL);state(m,TRUE,FALSE);
  g_object_unref(old);finish(m);g_object_unref(line);g_object_unref(off);cases++;
  /* 7: A stale initial client cannot replace the new owner's client. */
  m=start();appear();vanish();appear();complete_client(TRUE);g_assert_null(m->upower);complete_client(TRUE);
  complete_enum(TRUE,NULL,NULL);state(m,FALSE,FALSE);finish(m);cases++;
  /* 8: Disposing before either real async completion holds no manager alive. */
  m=start();appear();GWeakRef weak;g_weak_ref_init(&weak,m);g_object_unref(m);g_assert_null(g_weak_ref_get(&weak));complete_client(TRUE);g_weak_ref_clear(&weak);
  g_assert_cmpuint(watch.id,==,0);g_assert_true(g_queue_is_empty(&pending));
  m=start();appear();complete_client(TRUE);g_weak_ref_init(&weak,m);g_object_unref(m);g_assert_null(g_weak_ref_get(&weak));complete_enum(TRUE,NULL,NULL);g_weak_ref_clear(&weak);
  g_assert_true(g_queue_is_empty(&pending));cases++;
  /* 9: Initial failure does not busy-retry; a later owner generation reconnects. */
  m=start();appear();guint calls=new_client_calls;complete_client(FALSE);state(m,FALSE,FALSE);g_assert_cmpuint(new_client_calls,==,calls);
  vanish();appear();complete_client(TRUE);line=device_new("/line",UP_DEVICE_KIND_LINE_POWER,TRUE);complete_enum(TRUE,line,NULL);state(m,TRUE,TRUE);
  g_object_run_dispose(G_OBJECT(m));g_object_run_dispose(G_OBJECT(m));g_object_unref(m);g_object_unref(line);
  g_assert_true(g_queue_is_empty(&pending));g_assert_cmpuint(watch_starts,==,watch_stops);cases++;
  /* 10: A property observer may dispose during owner replacement. No new call. */
  m=start();appear();complete_client(TRUE);line=device_new("/line",UP_DEVICE_KIND_LINE_POWER,TRUE);complete_enum(TRUE,line,NULL);
  g_signal_connect(m,"notify::external-power-known",G_CALLBACK(dispose_on_unknown),NULL);calls=new_client_calls;
  appear();g_assert_true(m->disposed);g_assert_cmpuint(new_client_calls,==,calls);g_assert_true(g_queue_is_empty(&pending));
  g_object_unref(m);g_object_unref(line);g_assert_cmpuint(watch_starts,==,watch_stops);cases++;
  g_print("{\"passed\":true,\"actual_manager_groups\":%u,\"new_client_calls\":%u,\"enumeration_calls\":%u,\"signals_before_every_enumeration\":%u,\"watches_joined\":%u,\"fake_device_finalizations\":%u,\"fake_client_finalizations\":%u,\"real_glib_tasks_signals_weakrefs\":true,\"device_or_refresh_io\":false}\n",cases,new_client_calls,enum_calls,attached_before_enumeration,watch_stops,devices_freed,clients_freed);
  return 0;
}
