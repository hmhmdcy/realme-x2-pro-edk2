#!/usr/bin/env python3
"""One cross-process Properties.Set ABI case on a fresh private session bus."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import dbus
import dbus.mainloop.glib


RECEIVER = r'''
import json,sys
from pathlib import Path
from gi.repository import Gio,GLib
bus=Gio.DBusConnection.new_for_address_sync(sys.argv[1],Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT|Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION,None,None)
xml='<node><interface name="org.freedesktop.DBus.Properties"><method name="Set"><arg name="interface" type="s" direction="in"/><arg name="name" type="s" direction="in"/><arg name="value" type="v" direction="in"/></method></interface></node>'
info=Gio.DBusNodeInfo.new_for_xml(xml)
def called(connection,sender,path,interface,method,parameters,invocation):
    container=parameters.get_child_value(2)
    value=container.get_variant()
    Path(sys.argv[2]).write_text(json.dumps(dict(signature=parameters.get_type_string().strip('()'),interface=parameters.get_child_value(0).get_string(),name=parameters.get_child_value(1).get_string(),value=value.get_boolean(),value_container_type=container.get_type_string(),value_inner_type=value.get_type_string()))+'\n')
    invocation.return_value(GLib.Variant('()',()))
obj=bus.register_object('/org/bluez/hci0',info.interfaces[0],called,None,None)
print(json.dumps(dict(owner=bus.get_unique_name())),flush=True)
GLib.MainLoop().run()
'''


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--old-source', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path, help='New private directory; parent must exist')
    args = parser.parse_args()
    args.output.mkdir(mode=0o700, exist_ok=False)
    server = Path(__file__).with_name('phone-gatt-peer.py')
    old_sha = hashlib.sha256(args.old_source.read_bytes()).hexdigest()
    assert old_sha == 'cda475eae488dde656b53a07e473fd9076668c5fbcaa2d9397dc61a405eefe10'
    assert args.old_source.read_text().replace('dbus.Boolean(value),', 'dbus.Boolean(value, variant_level=1),') == server.read_text()
    sys.dont_write_bytecode = True
    old = load(args.old_source, 'properties_set_old')
    current = load(server, 'properties_set_current')
    daemon = receiver = connection = None
    try:
        daemon = subprocess.Popen(['dbus-daemon', '--session', '--nofork', '--print-address=1'],
                                  stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        address = daemon.stdout.readline().strip()
        assert address.startswith('unix:')
        observed_file = args.output / 'receiver-private.json'
        receiver = subprocess.Popen([sys.executable, '-B', '-c', RECEIVER, address, str(observed_file)],
                                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        owner = json.loads(receiver.stdout.readline())['owner']
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        connection = dbus.bus.BusConnection(address)
        calls = []
        def proxy(path):
            assert path == '/org/bluez/hci0'
            return connection.get_object(owner, path, introspect=False)
        native = SimpleNamespace(stopping=False, args=SimpleNamespace(adapter='/org/bluez/hci0'),
                                 require_capture=lambda: calls.append('capture-health-check'), proxy=proxy)
        try:
            old.PeerRun.set_adapter(native, 'Powered', True, 3)
            raise AssertionError('Old ssb call unexpectedly succeeded')
        except dbus.exceptions.DBusException as error:
            assert error.get_dbus_name() in ('org.freedesktop.DBus.Error.UnknownMethod', 'org.freedesktop.DBus.Error.InvalidArgs')
            assert 'ssb' in str(error)
            old_failure = error.get_dbus_name()
        assert not observed_file.exists(), 'ssb must not enter the ssv receiver'
        current.PeerRun.set_adapter(native, 'Powered', True, 3)
        observed = json.loads(observed_file.read_text())
        assert observed == {'signature': 'ssv', 'interface': 'org.bluez.Adapter1', 'name': 'Powered',
                            'value': True, 'value_container_type': 'v', 'value_inner_type': 'b'}
        assert calls == ['capture-health-check', 'capture-health-check']
        report = {'single_cross_process_case_passed': True,
                  'old_server_sha256': old_sha, 'server_sha256': hashlib.sha256(server.read_bytes()).hexdigest(),
                  'only_set_variant_argument_changed': True,
                  'strict_receiver': 'GIO GDBus register_object with ssv introspection',
                  'old_native_set_signature': 'ssb', 'old_failure': old_failure,
                  'old_call_did_not_enter_receiver': True, 'fixed_native_call_received': observed,
                  'both_actual_native_callers_checked_capture_health': True,
                  'used_only_new_private_session_bus': True, 'system_bus_or_phone_accessed': False,
                  'prior_nine_DBus_interface_checks_rerun': False, 'hardware_set_or_adapter_mutation_performed': False}
        (args.output / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report))
    finally:
        if connection:
            connection.close()
        for process in (receiver, daemon):
            if process and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2)


if __name__ == '__main__':
    main()
