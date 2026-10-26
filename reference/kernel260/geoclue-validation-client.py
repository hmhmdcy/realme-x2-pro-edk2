#!/usr/bin/env python3
"""Bounded UID10000 GeoClue diagnostic; never emit coordinates or GNSS epochs.

Use with an explicitly allowed diagnostic desktop entry and source configuration.
This corrects future captures; it does not reclassify the original260 field data.
"""
import json
import math
import os
import signal
import sys
import time


def quality(location, now, previous_stamp):
    """Zero reported accuracy is permitted; negative/unknown accuracy is rejected."""
    try:
        latitude, longitude, accuracy = (float(location[k]) for k in
                                         ['Latitude', 'Longitude', 'Accuracy'])
        if not all(math.isfinite(v) for v in [latitude, longitude, accuracy]):
            return dict(valid=False, reason='nonfinite'), previous_stamp
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            return dict(valid=False, reason='coordinate-range'), previous_stamp
        if accuracy < 0:
            return dict(valid=False, reason='unknown-accuracy'), previous_stamp
        seconds, microseconds = (int(v) for v in location['Timestamp'])
        if seconds <= 0 or not 0 <= microseconds < 1000000:
            return dict(valid=False, reason='timestamp-range'), previous_stamp
    except (KeyError, ValueError, TypeError, OverflowError):
        return dict(valid=False, reason='malformed-properties'), previous_stamp
    stamp = (seconds, microseconds)
    return dict(valid=True, reason='accepted', accuracy_m=accuracy,
                zero_reported_accuracy=accuracy == 0,
                timestamp_changed=stamp != previous_stamp,
                recent_timestamp=abs(now-(seconds+microseconds/1e6)) < 10), stamp


def main():
    import dbus
    from dbus.mainloop.glib import DBusGMainLoop
    from gi.repository import GLib, GLibUnix
    assert os.getuid() == 10000
    duration = int(sys.argv[1])
    assert 0 <= duration <= 900
    DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus(private=True)
    session = dbus.SessionBus(private=True)
    service = 'org.freedesktop.GeoClue2'
    manager = dbus.Interface(bus.get_object(service, '/org/freedesktop/GeoClue2/Manager'),
                             service+'.Manager')
    session_api = dbus.Interface(session.get_object('org.gnome.SessionManager',
                                '/org/gnome/SessionManager'), 'org.gnome.SessionManager')
    loop = GLib.MainLoop()
    result = dict(kind='result', collector_version=2, uid=os.getuid(),
                  location_events=0, valid_location_events=0, fresh_timestamp_events=0,
                  zero_accuracy_events=0, rejection_reasons={}, event_metadata=[])
    began = time.monotonic()
    previous_stamp = None
    path = None
    cookie = None
    client = None

    def changed(old, new):
        nonlocal previous_stamp
        result['location_events'] += 1
        try:
            location = dbus.Interface(bus.get_object(service, new),
                         'org.freedesktop.DBus.Properties').GetAll(service+'.Location')
            metadata, previous_stamp = quality(location, time.time(), previous_stamp)
        except dbus.DBusException:
            metadata = dict(valid=False, reason='properties-read-failed')
        metadata['elapsed_seconds'] = time.monotonic()-began
        result['event_metadata'].append(metadata)
        if metadata['valid']:
            result['valid_location_events'] += 1
            result['fresh_timestamp_events'] += int(metadata['timestamp_changed'] and
                                                     metadata['recent_timestamp'])
            result['zero_accuracy_events'] += int(metadata['zero_reported_accuracy'])
        else:
            reason = metadata['reason']
            result['rejection_reasons'][reason] = result['rejection_reasons'].get(reason, 0)+1

    def stop(*unused):
        loop.quit()
        return False

    try:
        cookie = session_api.Inhibit('org.realme.SamuraiGNSSValidation', dbus.UInt32(0),
                                    'Bounded GNSS validation', dbus.UInt32(12), timeout=10)
        path = manager.GetClient(timeout=25)
        obj = bus.get_object(service, path)
        client = dbus.Interface(obj, service+'.Client')
        props = dbus.Interface(obj, 'org.freedesktop.DBus.Properties')
        props.Set(service+'.Client', 'DesktopId', 'org.realme.SamuraiGNSSValidation')
        props.Set(service+'.Client', 'RequestedAccuracyLevel', dbus.UInt32(8))
        props.Set(service+'.Client', 'TimeThreshold', dbus.UInt32(1))
        client.connect_to_signal('LocationUpdated', changed)
        for sig in [signal.SIGINT, signal.SIGTERM]:
            GLibUnix.signal_add(GLib.PRIORITY_DEFAULT, sig, stop)
        client.Start(timeout=45)
        result['started'] = True
        GLib.timeout_add_seconds(duration, stop)
        loop.run()
    except dbus.DBusException as error:
        result['error_name'] = error.get_dbus_name()
    finally:
        if client is not None:
            try:
                client.Stop(timeout=20)
                result['stopped'] = True
            except dbus.DBusException as error:
                result['stop_error_name'] = error.get_dbus_name()
        if path is not None:
            try:
                manager.DeleteClient(path, timeout=10)
                result['client_deleted'] = True
            except dbus.DBusException as error:
                result['delete_error_name'] = error.get_dbus_name()
        if cookie is not None:
            session_api.Uninhibit(cookie, timeout=10)
        bus.close()
        session.close()
    result['elapsed_seconds'] = time.monotonic()-began
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
