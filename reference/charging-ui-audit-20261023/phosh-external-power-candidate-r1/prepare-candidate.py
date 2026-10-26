"""Create only a private candidate source/patch from the checksum-pinned release."""
from pathlib import Path
import difflib
import hashlib
import json

HERE = Path(__file__).resolve().parent
BASE = HERE.parent/'phosh-connection-source-r8'/'release-files'/'phosh'


def replace(text, before, after):
    if text.count(before) != 1:
        raise RuntimeError('non-unique source anchor: '+before[:60])
    return text.replace(before, after, 1)


def main():
    out = HERE/'candidate'
    if out.exists():
        raise RuntimeError('refuse overwrite candidate')
    changes = {}
    path = 'src/battery-manager.c'
    original = (BASE/path).read_text()
    text = replace(original, '  PROP_PERCENT,\n', '  PROP_PERCENT,\n  PROP_EXTERNAL_POWER_KNOWN,\n  PROP_EXTERNAL_POWER_CONNECTED,\n')
    text = replace(text, '  uint          percent;\n', '''  uint          percent;

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
''')
    text = replace(text, 'static void\non_up_client_new_ready (', (HERE/'manager-additions.c.inc').read_text()+'\n\nstatic void\non_up_client_new_ready (')
    text = replace(text, '  PhoshBatteryManager *self = PHOSH_BATTERY_MANAGER (data);\n', '''  g_autoptr (PowerRequest) request = data;
  g_autoptr (PhoshBatteryManager) self = g_weak_ref_get (&request->manager);
''')
    text = replace(text, '  UpClient *upower = NULL;\n', '  g_autoptr (UpClient) upower = NULL;\n')
    text = replace(text, '  upower = up_client_new_finish (result, &err);\n', '''  upower = up_client_new_finish (result, &err);
  if (!self || self->disposed || request->generation != self->power_generation)
    return;
''')
    text = replace(text, '  self->upower = upower;\n', '''  self->upower = g_steal_pointer (&upower);
  /* Attach signals before the asynchronous snapshot to close enumeration races. */
  g_signal_connect_object (self->upower, "device-added", G_CALLBACK (on_power_device_added), self, 0);
  g_signal_connect_object (self->upower, "device-removed", G_CALLBACK (on_power_device_removed), self, 0);
  rescan_power_devices (self);
''')
    text = replace(text, '  up_client_new_async (self->cancel, on_up_client_new_ready, self);\n', '''  self->power_watch = g_bus_watch_name (G_BUS_TYPE_SYSTEM, "org.freedesktop.UPower",
                                        G_BUS_NAME_WATCHER_FLAGS_AUTO_START,
                                        on_power_name_appeared, on_power_name_vanished,
                                        power_request_new (self), power_request_free);
''')
    text = replace(text, '  case PROP_PRESENT:\n', '''  case PROP_EXTERNAL_POWER_KNOWN:
    g_value_set_boolean (value, self->external_power_known);
    break;
  case PROP_EXTERNAL_POWER_CONNECTED:
    g_value_set_boolean (value, self->external_power_connected);
    break;
  case PROP_PRESENT:
''')
    text = replace(text, '''  g_cancellable_cancel (self->cancel);
  g_clear_object (&self->cancel);
  g_clear_object (&self->device);
  g_clear_object (&self->upower);
''', '''  self->disposed = TRUE;
  if (self->power_watch) {
    g_bus_unwatch_name (self->power_watch);
    self->power_watch = 0;
  }
  disconnect_power_client (self);
  g_clear_pointer (&self->power_devices, g_hash_table_unref);
''')
    text = replace(text, '  g_object_class_install_properties (object_class, PROP_LAST_PROP, props);', '''  props[PROP_EXTERNAL_POWER_KNOWN] =
    g_param_spec_boolean ("external-power-known", "", "Whether connection presence is known",
                          FALSE, G_PARAM_READABLE | G_PARAM_EXPLICIT_NOTIFY | G_PARAM_STATIC_STRINGS);
  props[PROP_EXTERNAL_POWER_CONNECTED] =
    g_param_spec_boolean ("external-power-connected", "", "External power is connected, not necessarily charging",
                          FALSE, G_PARAM_READABLE | G_PARAM_EXPLICIT_NOTIFY | G_PARAM_STATIC_STRINGS);

  g_object_class_install_properties (object_class, PROP_LAST_PROP, props);''')
    text = replace(text, 'phosh_battery_manager_init (PhoshBatteryManager *self)\n{\n  self->cancel = g_cancellable_new ();\n', 'phosh_battery_manager_init (PhoshBatteryManager *self)\n{\n  self->power_devices = g_hash_table_new_full (g_str_hash, g_str_equal, g_free, g_object_unref);\n')
    changes[path] = (original, text)
    path = 'src/top-panel.c'
    original = (BASE/path).read_text()
    text = replace(original, '#include "layersurface-priv.h"', '#include "battery-manager.h"\n#include "status-icon.h"\n#include "layersurface-priv.h"')
    text = replace(text, '  GtkWidget *batteryinfo;\n', '  GtkWidget *batteryinfo;\n  GtkWidget *external_power;\n  GtkWidget *external_power_icon;\n')
    anchor = '  G_OBJECT_CLASS (phosh_top_panel_parent_class)->constructed (object);\n'
    text = replace(text, anchor, anchor+'''
  g_object_bind_property (phosh_shell_get_battery_manager (shell), "external-power-connected",
                          self->external_power, "show-child", G_BINDING_SYNC_CREATE);
  atk_object_set_name (gtk_widget_get_accessible (self->external_power_icon),
                       _("External power connected"));
  atk_object_set_description (gtk_widget_get_accessible (self->external_power_icon),
                              _("The battery may still be discharging"));
''')
    anchor = '  gtk_widget_class_bind_template_child (widget_class, PhoshTopPanel, batteryinfo);\n'
    text = replace(text, anchor, anchor+'  gtk_widget_class_bind_template_child (widget_class, PhoshTopPanel, external_power);\n  gtk_widget_class_bind_template_child (widget_class, PhoshTopPanel, external_power_icon);\n')
    text = replace(text, '  g_type_ensure (PHOSH_TYPE_ARROW);', '  g_type_ensure (PHOSH_TYPE_STATUS_ICON);\n  g_type_ensure (PHOSH_TYPE_ARROW);')
    changes[path] = (original, text)
    path = 'src/ui/top-panel.ui'
    original = (BASE/path).read_text()
    text = replace(original, '  <requires lib="gtk+" version="3.24"/>\n', '''  <requires lib="gtk+" version="3.24"/>
  <object class="PhoshStatusIcon" id="external_power_icon">
    <property name="visible">0</property>
    <property name="pixel-size">16</property>
    <property name="priority">10</property>
    <property name="icon-name">external-power-connected-symbolic</property>
    <property name="tooltip-text" translatable="yes">External power connected; the battery may still be discharging</property>
  </object>
''')
    anchor = '''                            <child>
                              <object class="PhoshBatteryInfo" id="batteryinfo">'''
    text = replace(text, anchor, '''                            <child>
                              <object class="PhoshRevealer" id="external_power">
                                <property name="visible">1</property>
                                <property name="show-child">0</property>
                                <property name="transition-duration">0</property>
                                <property name="child">external_power_icon</property>
                              </object>
                            </child>
'''+anchor)
    changes[path] = (original, text)
    path = 'src/phosh.gresources.xml'
    original = (BASE/path).read_text()
    anchor = '  <gresource prefix="/mobi/phosh/icons/scalable/status/">\n'
    text = replace(original, anchor, anchor+'    <file alias="external-power-connected-symbolic.svg">../data/icons/external-power-connected-symbolic.svg</file>\n')
    changes[path] = (original, text)
    svg = '''<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
  <path fill="#2e3436" d="M5 1h2v4h2V1h2v4h2v2h-1v2a4 4 0 0 1-3 3.87V16H7v-3.13A4 4 0 0 1 4 9V7H3V5h2zm1 6v2a2 2 0 0 0 4 0V7z"/>
</svg>
'''
    changes['data/icons/external-power-connected-symbolic.svg'] = ('', svg)
    patch = ''
    pins = {}
    for path, (before, after) in changes.items():
        target = out/path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(after, newline='\n')
        patch += ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile='a/'+path if before else '/dev/null', tofile='b/'+path))
        pins[path] = {'base_sha256': hashlib.sha256(before.encode()).hexdigest() if before else None, 'candidate_sha256': hashlib.sha256(after.encode()).hexdigest()}
    # The existing battery icon selection callback is unchanged in full.
    start = original = (BASE/'src/battery-manager.c').read_text()
    a = start[start.index('static void\non_property_changed ('):start.index('\n\nstatic void\non_up_client_new_ready (')]
    assert a in changes['src/battery-manager.c'][1]
    (HERE/'external-power-marker.patch').write_text(patch, newline='\n')
    (HERE/'source-result.json').write_text(json.dumps({'files':pins,'old_battery_callback_unchanged':True,'default_build_or_device_actions':False},indent=2)+'\n')
    print(json.dumps({'files':pins,'patch_sha256':hashlib.sha256(patch.encode()).hexdigest()},indent=2))


if __name__ == '__main__':
    main()
