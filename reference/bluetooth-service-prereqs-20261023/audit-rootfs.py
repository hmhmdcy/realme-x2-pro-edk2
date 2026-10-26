#!/usr/bin/env python3
"""Read a stored rootfs's selected Bluetooth packages and files; no target execution."""
import argparse
import configparser
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rootfs', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path, help='New JSON file; parent must exist')
    args = parser.parse_args()
    root = args.rootfs
    database = root / 'lib/apk/db/installed'
    raw = database.read_bytes()
    wanted = {'bluez', 'bluez-openrc', 'bluez-btmon', 'bluez-btmgmt', 'bluez-obexd',
              'obexd-enhanced', 'obex-capabilities', 'gnome-bluetooth',
              'networkmanager', 'networkmanager-bluetooth', 'pulseaudio',
              'pulseaudio-bluez', 'pulseaudio-wireplumber', 'python3', 'py3-dbus',
              'py3-gobject3', 'gobject-introspection', 'glib'}
    packages = {}
    commands = {}
    command_names = {'btmon', 'btmgmt', 'bluetoothctl', 'bluetoothd', 'obexd', 'bluetooth-sendto'}
    for record in raw.decode().split('\n\n'):
        fields = dict(line.split(':', 1) for line in record.splitlines()
                      if line[:2] in ('P:', 'V:', 'c:', 'o:'))
        package = fields.get('P')
        if package in wanted:
            packages[package] = {'version': fields.get('V'), 'origin': fields.get('o'),
                                 'packaging_commit': fields.get('c')}
        directory = ''
        for line in record.splitlines():
            if line.startswith('F:'):
                directory = line[2:]
            elif line.startswith('R:') and line[2:] in command_names:
                name = directory + '/' + line[2:]
                commands[name] = {'owner': package, 'file_exists': (root / name).is_file()}

    paths = ['etc/bluetooth/main.conf', 'etc/bluetooth/input.conf', 'etc/bluetooth/network.conf',
             'etc/pulse/default.pa', 'usr/share/wireplumber/wireplumber.conf.d/51-pulseaudio.conf',
             'usr/share/dbus-1/services/org.bluez.obex.service',
             'usr/share/dbus-1/system-services/org.bluez.service',
             'usr/lib/girepository-1.0/GLibUnix-2.0.typelib']
    files = {}
    for relative in paths:
        path = root / relative
        files[relative] = {'exists': path.is_file()}
        if path.is_file():
            files[relative]['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()

    main_conf = configparser.ConfigParser()
    main_conf.read(root / 'etc/bluetooth/main.conf')
    pulse = (root / 'etc/pulse/default.pa').read_text()
    wp = (root / 'usr/share/wireplumber/wireplumber.conf.d/51-pulseaudio.conf').read_text()
    obex = (root / 'usr/share/dbus-1/services/org.bluez.obex.service').read_text()
    activation = (root / 'usr/share/dbus-1/system-services/org.bluez.service').read_text()
    report = {'scope': 'stored-rootfs-only-not-current-device',
              'apk_database_sha256': hashlib.sha256(raw).hexdigest(),
              'packages': packages, 'selected_command_owners': commands, 'selected_files': files,
              'main_conf_explicit_controller_mode': main_conf.get('General', 'ControllerMode', fallback=None),
              'pulse_default_loads_bluetooth_policy': 'load-module module-bluetooth-policy' in pulse,
              'pulse_default_loads_bluetooth_discover': 'load-module module-bluetooth-discover' in pulse,
              'wireplumber_hardware_bluetooth_disabled': 'hardware.bluetooth = disabled' in wp,
              'wireplumber_hardware_audio_disabled': 'hardware.audio = disabled' in wp,
              'obex_user_session_activation_file': 'Name=org.bluez.obex' in obex,
              'bluez_system_activation_exec_false': 'Exec=/bin/false' in activation,
              'dbus_python_module_present': bool(list(root.glob('usr/lib/python*/site-packages/dbus/__init__.py'))),
              'pygobject_module_present': bool(list(root.glob('usr/lib/python*/site-packages/gi/__init__.py'))),
              'btmon_in_package_database': any(Path(p).name == 'btmon' for p in commands),
              'btmgmt_in_package_database': any(Path(p).name == 'btmgmt' for p in commands),
              'phone_sdk_or_radio_accessed': False, 'target_binaries_executed': False,
              'runtime_or_feature_pass_claimed': False}
    with args.output.open('x') as output:
        output.write(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'stored_rootfs_read_only_audit': True, 'selected_packages': len(packages),
                      'btmon_in_package_database': report['btmon_in_package_database'],
                      'obexd_owner': commands.get('usr/lib/bluetooth/obexd', {}).get('owner'),
                      'runtime_or_feature_pass_claimed': False}))


if __name__ == '__main__':
    main()
