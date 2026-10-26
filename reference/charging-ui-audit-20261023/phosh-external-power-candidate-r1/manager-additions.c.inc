/* Connection presence is independent of net battery charge and its icon. */
typedef struct {
  GWeakRef manager;
  guint64 generation;
  guint64 topology;
} PowerRequest;

static void rescan_power_devices (PhoshBatteryManager *self);
static void on_up_client_new_ready (GObject *source, GAsyncResult *result, gpointer data);

static PowerRequest *
power_request_new (PhoshBatteryManager *self)
{
  PowerRequest *request = g_new0 (PowerRequest, 1);

  g_weak_ref_init (&request->manager, self);
  request->generation = self->power_generation;
  request->topology = self->power_topology;
  return request;
}

static void
power_request_free (gpointer data)
{
  PowerRequest *request = data;

  g_weak_ref_clear (&request->manager);
  g_free (request);
}
G_DEFINE_AUTOPTR_CLEANUP_FUNC (PowerRequest, power_request_free)

static void
update_external_power (PhoshBatteryManager *self)
{
  GHashTableIter iter;
  gpointer value;
  gboolean have_line = FALSE, unknown_kind = FALSE, connected = FALSE, known;

  if (self->power_owner && self->power_devices) {
    g_hash_table_iter_init (&iter, self->power_devices);
    while (g_hash_table_iter_next (&iter, NULL, &value)) {
      guint kind;
      gboolean online;

      g_object_get (value, "kind", &kind, "online", &online, NULL);
      unknown_kind |= kind == UP_DEVICE_KIND_UNKNOWN;
      if (kind != UP_DEVICE_KIND_LINE_POWER)
        continue;
      have_line = TRUE;
      connected |= online;
    }
  }

  /* An observed online device is sufficient for connected. Proving offline
   * needs a current complete enumeration, not just an empty/failed snapshot. */
  known = self->power_owner &&
          (connected || (self->power_enumerated && have_line && !unknown_kind));
  connected = known && connected;
  g_object_freeze_notify (G_OBJECT (self));
  if (self->external_power_known != known) {
    self->external_power_known = known;
    g_object_notify_by_pspec (G_OBJECT (self), props[PROP_EXTERNAL_POWER_KNOWN]);
  }
  if (self->external_power_connected != connected) {
    self->external_power_connected = connected;
    g_object_notify_by_pspec (G_OBJECT (self), props[PROP_EXTERNAL_POWER_CONNECTED]);
  }
  g_object_thaw_notify (G_OBJECT (self));
}

static void
on_power_device_notify (PhoshBatteryManager *self, GParamSpec *pspec, UpDevice *device)
{
  if (!self->disposed)
    update_external_power (self);
}

static void
clear_power_devices (PhoshBatteryManager *self)
{
  GHashTableIter iter;
  gpointer value;

  if (!self->power_devices)
    return;
  g_hash_table_iter_init (&iter, self->power_devices);
  while (g_hash_table_iter_next (&iter, NULL, &value))
    g_signal_handlers_disconnect_by_func (value, on_power_device_notify, self);
  g_hash_table_remove_all (self->power_devices);
}

static void
track_power_device (PhoshBatteryManager *self, UpDevice *device)
{
  const char *path = up_device_get_object_path (device);
  UpDevice *old;

  if (!path)
    return;
  old = g_hash_table_lookup (self->power_devices, path);
  if (old == device)
    return;
  if (old)
    g_signal_handlers_disconnect_by_func (old, on_power_device_notify, self);
  g_hash_table_replace (self->power_devices, g_strdup (path), g_object_ref (device));
  g_signal_connect_object (device, "notify::online", G_CALLBACK (on_power_device_notify),
                           self, G_CONNECT_SWAPPED);
  g_signal_connect_object (device, "notify::kind", G_CALLBACK (on_power_device_notify),
                           self, G_CONNECT_SWAPPED);
}

static void
on_power_devices_ready (GObject *source, GAsyncResult *result, gpointer data)
{
  g_autoptr (PowerRequest) request = data;
  g_autoptr (PhoshBatteryManager) self = g_weak_ref_get (&request->manager);
  g_autoptr (GError) error = NULL;
  g_autoptr (GPtrArray) devices = up_client_get_devices_finish (UP_CLIENT (source), result, &error);

  if (!self || self->disposed || request->generation != self->power_generation ||
      request->topology != self->power_topology || source != G_OBJECT (self->upower))
    return;

  g_clear_object (&self->line_cancel);
  self->power_enumerated = devices != NULL;
  if (devices) {
    clear_power_devices (self);
    for (guint i = 0; i < devices->len; i++)
      track_power_device (self, g_ptr_array_index (devices, i));
  }
  update_external_power (self);
}

static void
rescan_power_devices (PhoshBatteryManager *self)
{
  if (self->disposed || !self->power_owner || !self->upower)
    return;
  if (self->line_cancel)
    g_cancellable_cancel (self->line_cancel);
  g_clear_object (&self->line_cancel);
  self->line_cancel = g_cancellable_new ();
  self->power_enumerated = FALSE;
  up_client_get_devices_async (self->upower, self->line_cancel,
                               on_power_devices_ready, power_request_new (self));
  update_external_power (self);
}

static void
on_power_device_added (UpClient *client, UpDevice *device, PhoshBatteryManager *self)
{
  if (self->disposed || !self->power_owner || client != self->upower)
    return;
  self->power_topology++;
  track_power_device (self, device);
  rescan_power_devices (self);
}

static void
on_power_device_removed (UpClient *client, const char *path, PhoshBatteryManager *self)
{
  UpDevice *device;

  if (self->disposed || !self->power_owner || client != self->upower)
    return;
  self->power_topology++;
  device = g_hash_table_lookup (self->power_devices, path);
  if (device)
    g_signal_handlers_disconnect_by_func (device, on_power_device_notify, self);
  g_hash_table_remove (self->power_devices, path);
  rescan_power_devices (self);
}

static void
disconnect_power_client (PhoshBatteryManager *self)
{
  /* Invalidate before cancellation: old completions may still be dispatched. */
  self->power_generation++;
  self->power_topology++;
  self->power_owner = self->power_enumerated = FALSE;
  if (self->line_cancel)
    g_cancellable_cancel (self->line_cancel);
  if (self->cancel)
    g_cancellable_cancel (self->cancel);
  g_clear_object (&self->line_cancel);
  g_clear_object (&self->cancel);
  clear_power_devices (self);
  if (self->upower)
    g_signal_handlers_disconnect_by_data (self->upower, self);
  if (self->device)
    g_signal_handlers_disconnect_by_func (self->device, on_property_changed, self);
  g_clear_object (&self->device);
  g_clear_object (&self->upower);
  /* Retain the last battery icon; this is not a synthetic Battery State. */
  update_external_power (self);
}

static void
on_power_name_appeared (GDBusConnection *connection, const char *name,
                       const char *owner, gpointer data)
{
  PowerRequest *watch = data;
  g_autoptr (PhoshBatteryManager) self = g_weak_ref_get (&watch->manager);

  if (!self || self->disposed)
    return;
  disconnect_power_client (self);
  if (self->disposed)
    return; /* A connection-property observer may have disposed us. */
  self->power_owner = TRUE;
  self->cancel = g_cancellable_new ();
  /* A fresh client follows this service owner, without keeping old proxies. */
  up_client_new_async (self->cancel, on_up_client_new_ready, power_request_new (self));
}

static void
on_power_name_vanished (GDBusConnection *connection, const char *name, gpointer data)
{
  PowerRequest *watch = data;
  g_autoptr (PhoshBatteryManager) self = g_weak_ref_get (&watch->manager);

  if (self && !self->disposed)
    disconnect_power_client (self);
}
