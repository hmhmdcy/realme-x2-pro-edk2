#!/usr/bin/env python3
"""Exercise the real exported methods on a new host-only private D-Bus.

No system bus, bluetoothd, controller, Windows radio, or phone is accessed.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import signal
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET

import dbus
import dbus.mainloop.glib
from gi.repository import GLib

ROOT = '/com/rmx1931/letest'
RX = ROOT + '/service0/char0'
TX = ROOT + '/service0/char1'
PEER = ROOT + '/offline_peer'
CHAR = 'org.bluez.GattCharacteristic1'
PROPS = 'org.freedesktop.DBus.Properties'
PREFIX = b'RMX1931-LE:'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, help='New absolute private result directory')
    args = parser.parse_args()
    os.umask(0o077)
    out = Path(args.output)
    assert out.is_absolute()
    out.mkdir(mode=0o700, parents=False, exist_ok=False)
    server = Path(__file__).with_name('phone-gatt-peer.py')
    daemon = worker = connection = None
    checks = []
    notifications = []
    try:
        daemon = subprocess.Popen(['dbus-daemon', '--session', '--nofork', '--print-address=1'],
                                  stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        address = daemon.stdout.readline().strip()
        assert address.startswith('unix:')
        worker = subprocess.Popen([sys.executable, str(server), '--offline-export', '--bus-address', address,
                                   '--output', str(out / 'exported-fixture'), '--seconds', '30'],
                                  stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        first = json.loads(worker.stdout.readline())
        assert first['no_bluez_or_radio_access'] is True
        owner = first['offline_unique_name']
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        connection = dbus.bus.BusConnection(address)
        app = connection.get_object(owner, ROOT, introspect=False)
        objects = app.GetManagedObjects(dbus_interface='org.freedesktop.DBus.ObjectManager', timeout=3)
        assert set(map(str, objects)) == {ROOT + '/service0', RX, TX}
        assert list(objects[RX][CHAR]['Flags']) == ['read', 'write']
        assert list(objects[TX][CHAR]['Flags']) == ['read', 'notify']
        checks.append('ObjectManager exports one primary service and exact RX/TX flags')
        rx = connection.get_object(owner, RX, introspect=False)
        tx = connection.get_object(owner, TX, introspect=False)
        xml = tx.Introspect(dbus_interface='org.freedesktop.DBus.Introspectable', timeout=3)
        tree = ET.fromstring(str(xml))
        methods = {m.attrib['name']: [(a.attrib['direction'], a.attrib['type']) for a in m.findall('arg')]
                   for m in tree.findall('./interface[@name="org.bluez.GattCharacteristic1"]/method')}
        assert methods['ReadValue'] == [('in', 'a{sv}'), ('out', 'ay')]
        assert methods['WriteValue'] == [('in', 'ay'), ('in', 'a{sv}')]
        assert methods['StartNotify'] == [] and methods['StopNotify'] == []
        checks.append('Actual D-Bus introspection matches BlueZ 5.87 method signatures')

        def opts(**overrides):
            result = {'device': dbus.ObjectPath(PEER), 'link': 'LE', 'offset': dbus.UInt16(0), 'mtu': dbus.UInt16(23), 'type': 'request'}
            result.update(overrides)
            return dbus.Dictionary(result, signature='sv')

        def read(obj, options):
            return bytes(obj.ReadValue(options, dbus_interface=CHAR, timeout=3))

        def write(value, options):
            rx.WriteValue(dbus.ByteArray(value), options, dbus_interface=CHAR, timeout=3)

        def rejects(function, expected):
            try:
                function()
            except dbus.exceptions.DBusException as error:
                assert error.get_dbus_name() == 'org.bluez.Error.' + expected, str(error)
            else:
                raise AssertionError('Expected D-Bus rejection: ' + expected)

        def changed(interface, changed, invalidated):
            if str(interface) == CHAR and 'Value' in changed:
                notifications.append(bytes(changed['Value']))

        connection.add_signal_receiver(changed, signal_name='PropertiesChanged', dbus_interface=PROPS,
                                       path=TX, bus_name=owner)

        def pump():
            loop = GLib.MainLoop()
            GLib.timeout_add(80, lambda: (loop.quit(), False)[1])
            loop.run()

        ready = PREFIX + b'READY'
        assert read(tx, opts()) == ready
        assert read(tx, opts(offset=dbus.UInt16(len(ready)))) == b''
        rejects(lambda: read(tx, opts(offset=dbus.UInt16(len(ready) + 1))), 'InvalidOffset')
        rejects(lambda: read(tx, opts(device=dbus.ObjectPath(ROOT + '/foreign_peer'))), 'NotAuthorized')
        checks.append('Read offsets, end-of-value, invalid offset, and explicit peer gate')
        baseline = PREFIX + struct.pack('<I', 1) + bytes(range(5))
        extended = PREFIX + struct.pack('<I', 2) + bytes(range(32))
        assert len(baseline) == 20 and len(extended) == 47
        rejects(lambda: write(baseline, opts()), 'NotPermitted')
        tx.StartNotify(dbus_interface=CHAR, timeout=3)
        pump()
        assert notifications == []
        checks.append('StartNotify emits no READY Value and writes require subscription')
        write(baseline, opts())
        pump()
        assert notifications == [baseline]
        assert read(rx, opts()) == baseline and read(tx, opts()) == baseline
        assert read(rx, opts(offset=dbus.UInt16(10))) == baseline[10:]
        checks.append('20-byte challenge seq1: actual Value signal plus RX/TX readback and offset slice')
        for override in [{'offset': dbus.UInt16(1)}, {'prepare-authorize': dbus.Boolean(True)},
                         {'type': 'reliable'}, {'type': 'command'}]:
            rejects(lambda override=override: write(baseline, opts(**override)), 'NotSupported')
        rejects(lambda: write(baseline[:-1], opts()), 'InvalidValueLength')
        rejects(lambda: write(b'X' + baseline[1:], opts()), 'NotPermitted')
        rejects(lambda: write(PREFIX + struct.pack('<I', 0) + bytes(range(5)), opts()), 'NotPermitted')
        rejects(lambda: write(extended, opts(mtu=dbus.UInt16(49))), 'InvalidValueLength')
        missing_mtu = opts()
        del missing_mtu['mtu']
        rejects(lambda: write(extended, missing_mtu), 'InvalidValueLength')
        pump()
        assert notifications == [baseline]
        checks.append('Reject nonzero/prepare/reliable/command writes, invalid payload, and 47-byte MTU<50 or absent')
        write(extended, opts(mtu=dbus.UInt16(50)))
        pump()
        assert notifications == [baseline, extended]
        assert read(rx, opts(mtu=dbus.UInt16(50))) == extended
        assert read(tx, opts(mtu=dbus.UInt16(50))) == extended
        checks.append('47-byte challenge seq2: exact signal/readback only with explicit MTU50')
        tx.StopNotify(dbus_interface=CHAR, timeout=3)
        rejects(lambda: write(baseline, opts()), 'NotPermitted')
        checks.append('StopNotify prevents later test writes')
        worker.send_signal(signal.SIGTERM)
        tail, stderr = worker.communicate(timeout=5)
        (out / 'fixture-stdout-private.txt').write_text(json.dumps(first) + '\n' + tail)
        (out / 'fixture-stderr-private.txt').write_text(stderr)
        assert worker.returncode == 0 and not stderr, stderr
        assert not connection.name_has_owner(owner)
        report = json.loads((out / 'exported-fixture/summary-private.json').read_text())
        assert report['cleanup']['private_bus_closed'] is True
        assert report['notification_signals_emitted'] == 2
        assert len(report['accepted_writes']) == 2
        checks.append('SIGTERM removes exported objects and closes the private owner connection')
        result = {'offline_api_passed': True, 'checks': checks, 'check_count': len(checks),
                  'server_sha256': hashlib.sha256(server.read_bytes()).hexdigest(),
                  'used_only_new_private_session_bus': True, 'system_bus_accessed': False,
                  'phone_accessed': False, 'radio_advertising_or_connection_performed': False,
                  'hardware_le_passed': False}
        (out / 'validation.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result))
    finally:
        if connection:
            connection.close()
        if worker and worker.poll() is None:
            worker.send_signal(signal.SIGTERM)
            worker.communicate(timeout=5)
        if daemon:
            daemon.terminate()
            daemon.communicate(timeout=3)


if __name__ == '__main__':
    main()
