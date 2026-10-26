/*
 * Copyright (C) 2025 Phosh.mobi e.V.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 *
 * Author: Guido Günther <agx@sigxcpu.org>
 */

#define G_LOG_DOMAIN "phosh-battery-manager"

#include "phosh-config.h"
#include "battery-manager.h"

#include "upower.h"

#include <math.h>

/**
 * PhoshBatteryManager:
 *
 * Track batteries and their charging state
 */

enum {
  PROP_0,
  PROP_PRESENT,
  PROP_ICON_NAME,
  PROP_PERCENT,
  PROP_EXTERNAL_POWER_KNOWN,
  PROP_EXTERNAL_POWER_CONNECTED,
  PROP_LAST_PROP
};
static GParamSpec *props[PROP_LAST_PROP];

struct _PhoshBatteryManager {
  PhoshManager  parent;

  UpClient     *upower;
  UpDevice     *device;
  GCancellable *cancel;

  gboolean      present;
  char         *icon_name;
  uint          percent;

  GHashTable   *power_devices;
  GCancellable *line_cancel;
  guint         power_watch;
  guint64       power_generation;
  guint64       power_topology;
  gboolean      power_owner;
  gboolean      power_enumerated;
  gboolean      external_power_known;
  gboolean      external_power_connected;
  gboolean      disposed;
};
G_DEFINE_TYPE (PhoshBatteryManager, phosh_battery_manager, PHOSH_TYPE_MANAGER)


static void
on_property_changed (PhoshBatteryManager *self,
                     GParamSpec          *pspec,
                     UpDevice            *device)
{
  UpDeviceState state;
  double percentage;
  int smallest_ten;
  uint percent;
  gboolean is_charging;
  gboolean is_charged;
  g_autofree char *icon_name = NULL;

  g_object_get (device, "state", &state, "percentage", &percentage, NULL);

  is_charging = state == UP_DEVICE_STATE_CHARGING;
  smallest_ten = floor (percentage / 10.0) * 10;
  is_charged = state == UP_DEVICE_STATE_FULLY_CHARGED || (is_charging && smallest_ten == 100);

  if (is_charged) {
    icon_name = g_strdup ("battery-level-100-charged-symbolic");
  } else {
    if (is_charging)
      icon_name = g_strdup_printf ("battery-level-%d-charging-symbolic", smallest_ten);
    else
      icon_name = g_strdup_printf ("battery-level-%d-symbolic", smallest_ten);
  }

  if (g_strcmp0 (self->icon_name, icon_name)) {
    g_free (self->icon_name);
    self->icon_name = g_steal_pointer (&icon_name);
    g_debug ("New icon: %s", self->icon_name);
    g_object_notify_by_pspec (G_OBJECT (self), props[PROP_ICON_NAME]);
  }

  percent = (int) (percentage + 0.5);
  if (self->percent != percent) {
    self->percent = percent;
    g_object_notify_by_pspec (G_OBJECT (self), props[PROP_PERCENT]);
  }
}


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


static void
on_up_client_new_ready (GObject *source, GAsyncResult *result, gpointer data)
{
  g_autoptr (PowerRequest) request = data;
  g_autoptr (PhoshBatteryManager) self = g_weak_ref_get (&request->manager);
  g_autoptr (GError) err = NULL;
  g_autoptr (UpClient) upower = NULL;

  upower = up_client_new_finish (result, &err);
  if (!self || self->disposed || request->generation != self->power_generation)
    return;
  if (!upower) {
    g_message ("Failed to get UPower Client: %s", err->message);
    return;
  }

  self->upower = g_steal_pointer (&upower);
  /* Attach signals before the asynchronous snapshot to close enumeration races. */
  g_signal_connect_object (self->upower, "device-added", G_CALLBACK (on_power_device_added), self, 0);
  g_signal_connect_object (self->upower, "device-removed", G_CALLBACK (on_power_device_removed), self, 0);
  rescan_power_devices (self);

  /* TODO: this is a oversimplified sync call */
  self->device = up_client_get_display_device (self->upower);
  if (self->device == NULL) {
    g_warning ("Failed to get upowerd display device");
    return;
  }

  g_debug ("Got upower display device");
  g_object_connect (self->device,
                    "swapped-object-signal::notify::percentage",
                    G_CALLBACK (on_property_changed),
                    self,
                    "swapped-object-signal::notify::state",
                    G_CALLBACK (on_property_changed),
                    self,
                    NULL);

  self->present = TRUE;
  on_property_changed (self, NULL, self->device);
  g_object_notify_by_pspec (G_OBJECT (self), props[PROP_PRESENT]);
}


static void
phosh_battery_manager_idle_init (PhoshManager *manager)
{
  PhoshBatteryManager *self = PHOSH_BATTERY_MANAGER (manager);

  self->power_watch = g_bus_watch_name (G_BUS_TYPE_SYSTEM, "org.freedesktop.UPower",
                                        G_BUS_NAME_WATCHER_FLAGS_AUTO_START,
                                        on_power_name_appeared, on_power_name_vanished,
                                        power_request_new (self), power_request_free);
}


static void
phosh_battery_manager_get_property (GObject    *object,
                                    guint       property_id,
                                    GValue     *value,
                                    GParamSpec *pspec)
{
  PhoshBatteryManager *self = PHOSH_BATTERY_MANAGER (object);

  switch (property_id) {
  case PROP_EXTERNAL_POWER_KNOWN:
    g_value_set_boolean (value, self->external_power_known);
    break;
  case PROP_EXTERNAL_POWER_CONNECTED:
    g_value_set_boolean (value, self->external_power_connected);
    break;
  case PROP_PRESENT:
    g_value_set_boolean (value, self->present);
    break;
  case PROP_ICON_NAME:
    g_value_set_string (value, self->icon_name);
    break;
  case PROP_PERCENT:
    g_value_set_uint (value, self->percent);
    break;
  default:
    G_OBJECT_WARN_INVALID_PROPERTY_ID (object, property_id, pspec);
    break;
  }
}


static void
phosh_battery_manager_dispose (GObject *object)
{
  PhoshBatteryManager *self = PHOSH_BATTERY_MANAGER (object);

  self->disposed = TRUE;
  if (self->power_watch) {
    g_bus_unwatch_name (self->power_watch);
    self->power_watch = 0;
  }
  disconnect_power_client (self);
  g_clear_pointer (&self->power_devices, g_hash_table_unref);

  g_clear_pointer (&self->icon_name, g_free);

  G_OBJECT_CLASS (phosh_battery_manager_parent_class)->dispose (object);
}


static void
phosh_battery_manager_class_init (PhoshBatteryManagerClass *klass)
{
  GObjectClass *object_class = G_OBJECT_CLASS (klass);
  PhoshManagerClass *manager_class = PHOSH_MANAGER_CLASS (klass);

  object_class->get_property = phosh_battery_manager_get_property;
  object_class->dispose = phosh_battery_manager_dispose;

  manager_class->idle_init = phosh_battery_manager_idle_init;

  /**
   * PhoshBatteryManager:present
   *
   * Whether battery information is present
   */
  props[PROP_PRESENT] =
    g_param_spec_boolean ("present", "", "",
                          FALSE,
                          G_PARAM_READABLE | G_PARAM_EXPLICIT_NOTIFY | G_PARAM_STATIC_STRINGS);
  /**
   * PhoshBatteryManager:icon-name:
   *
   * The battery indicator icon name
   */
  props[PROP_ICON_NAME] =
    g_param_spec_string ("icon-name", "", "",
                         NULL,
                         G_PARAM_READABLE | G_PARAM_EXPLICIT_NOTIFY | G_PARAM_STATIC_STRINGS);
  /**
   * PhoshBatteryManager:percent:
   *
   * The charge percentage of the main battery
   */
  props[PROP_PERCENT] =
    g_param_spec_uint ("percent", "", "",
                       0, G_MAXUINT, 0,
                       G_PARAM_READABLE | G_PARAM_EXPLICIT_NOTIFY | G_PARAM_STATIC_STRINGS);

  props[PROP_EXTERNAL_POWER_KNOWN] =
    g_param_spec_boolean ("external-power-known", "", "Whether connection presence is known",
                          FALSE, G_PARAM_READABLE | G_PARAM_EXPLICIT_NOTIFY | G_PARAM_STATIC_STRINGS);
  props[PROP_EXTERNAL_POWER_CONNECTED] =
    g_param_spec_boolean ("external-power-connected", "", "External power is connected, not necessarily charging",
                          FALSE, G_PARAM_READABLE | G_PARAM_EXPLICIT_NOTIFY | G_PARAM_STATIC_STRINGS);

  g_object_class_install_properties (object_class, PROP_LAST_PROP, props);
}


static void
phosh_battery_manager_init (PhoshBatteryManager *self)
{
  self->power_devices = g_hash_table_new_full (g_str_hash, g_str_equal, g_free, g_object_unref);
}


PhoshBatteryManager *
phosh_battery_manager_new (void)
{
  return g_object_new (PHOSH_TYPE_BATTERY_MANAGER, NULL);
}
