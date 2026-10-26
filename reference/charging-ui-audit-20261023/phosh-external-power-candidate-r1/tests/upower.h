#pragma once
#include <gio/gio.h>
typedef enum { UP_DEVICE_KIND_UNKNOWN, UP_DEVICE_KIND_LINE_POWER, UP_DEVICE_KIND_BATTERY } UpDeviceKind;
typedef enum { UP_DEVICE_STATE_UNKNOWN, UP_DEVICE_STATE_CHARGING, UP_DEVICE_STATE_DISCHARGING,
               UP_DEVICE_STATE_EMPTY, UP_DEVICE_STATE_FULLY_CHARGED } UpDeviceState;
G_DECLARE_FINAL_TYPE (UpDevice, up_device, UP, DEVICE, GObject)
G_DECLARE_FINAL_TYPE (UpClient, up_client, UP, CLIENT, GObject)
#define UP_TYPE_DEVICE (up_device_get_type ())
#define UP_TYPE_CLIENT (up_client_get_type ())
void up_client_new_async (GCancellable *cancel, GAsyncReadyCallback callback, gpointer data);
UpClient *up_client_new_finish (GAsyncResult *result, GError **error);
void up_client_get_devices_async (UpClient *client, GCancellable *cancel, GAsyncReadyCallback callback, gpointer data);
GPtrArray *up_client_get_devices_finish (UpClient *client, GAsyncResult *result, GError **error);
UpDevice *up_client_get_display_device (UpClient *client);
const char *up_device_get_object_path (UpDevice *device);
