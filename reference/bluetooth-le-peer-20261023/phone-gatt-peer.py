#!/usr/bin/env python3
"""Bounded BlueZ 5.87 GATT peripheral for one explicitly named Windows peer.

The desktop offline-export mode uses a supplied private session bus only. It
does not contact BlueZ, register radio advertising, or access Bluetooth keys.
"""
import argparse
import configparser
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import struct
import subprocess
import sys
import time
import threading

import dbus
import dbus.mainloop.glib
import dbus.service
from gi.repository import GLib, GLibUnix

SERVICE_UUID = 'f0d19310-7a52-4d3f-9b14-0e4bb7f30001'
RX_UUID = 'f0d19310-7a52-4d3f-9b14-0e4bb7f30002'
TX_UUID = 'f0d19310-7a52-4d3f-9b14-0e4bb7f30003'
PREFIX = b'RMX1931-LE:'
READY = PREFIX + b'READY'
ROOT = '/com/rmx1931/letest'
ADV_PATH = ROOT + '/advertisement'
SERVICE_PATH = ROOT + '/service0'
RX_PATH = SERVICE_PATH + '/char0'
TX_PATH = SERVICE_PATH + '/char1'
OFFLINE_PEER = ROOT + '/offline_peer'
PROPERTIES = 'org.freedesktop.DBus.Properties'
OBJECT_MANAGER = 'org.freedesktop.DBus.ObjectManager'
SERVICE_IFACE = 'org.bluez.GattService1'
CHAR_IFACE = 'org.bluez.GattCharacteristic1'
ADV_IFACE = 'org.bluez.LEAdvertisement1'
ADAPTER_IFACE = 'org.bluez.Adapter1'
DEVICE_IFACE = 'org.bluez.Device1'
GATT_MANAGER = 'org.bluez.GattManager1'
ADV_MANAGER = 'org.bluez.LEAdvertisingManager1'
EXPECTED_RELEASE = '7.3.0-rc6-rmx1931-samurai-k363+'
CHARGING_MANIFEST = Path('/usr/share/samurai-charging/manifest.json')


class InvalidArguments(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.InvalidArguments'


class InvalidOffset(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.InvalidOffset'


class InvalidValueLength(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.InvalidValueLength'


class NotAuthorized(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.NotAuthorized'


class NotPermitted(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.NotPermitted'


class NotSupported(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.NotSupported'


def payload_sequence(value):
    """Validate the two entire, public challenge formats; no long-write assembly."""
    if len(value) not in (20, 47):
        raise InvalidValueLength('Only the complete 20-byte or 47-byte challenge is supported')
    if value[:11] != PREFIX or value[15:] != bytes(range(len(value) - 15)):
        raise NotPermitted('Challenge prefix or fixed pattern does not match')
    seq = struct.unpack_from('<I', value, 11)[0]
    if not 1 <= seq <= 16:
        raise NotPermitted('Challenge sequence must be 1 through 16')
    return seq


class PropertyObject(dbus.service.Object):
    def __init__(self, bus, path, interface):
        self.path = path
        self.interface = interface
        super().__init__(bus, path)

    def properties(self):
        raise NotImplementedError

    @dbus.service.method(PROPERTIES, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != self.interface:
            raise InvalidArguments('Unsupported interface')
        return self.properties()

    @dbus.service.method(PROPERTIES, in_signature='ss', out_signature='v')
    def Get(self, interface, name):
        props = self.GetAll(interface)
        if name not in props:
            raise InvalidArguments('Unknown property')
        return props[name]

    @dbus.service.method(PROPERTIES, in_signature='ssv', out_signature='')
    def Set(self, interface, name, value):
        raise NotPermitted('All exported test properties are read only')

    @dbus.service.signal(PROPERTIES, signature='sa{sv}as')
    def PropertiesChanged(self, interface, changed, invalidated):
        pass


class Characteristic(PropertyObject):
    def __init__(self, bus, context, role):
        self.context = context
        self.role = role
        self.value = b'' if role == 'rx' else READY
        self.notifying = False
        super().__init__(bus, RX_PATH if role == 'rx' else TX_PATH, CHAR_IFACE)

    def properties(self):
        props = {
            'UUID': RX_UUID if self.role == 'rx' else TX_UUID,
            'Service': dbus.ObjectPath(SERVICE_PATH),
            'Flags': dbus.Array(['read', 'write'] if self.role == 'rx' else ['read', 'notify'], signature='s'),
            'Value': dbus.ByteArray(self.value),
        }
        if self.role == 'tx':
            props['Notifying'] = dbus.Boolean(self.notifying)
        return props

    @dbus.service.method(CHAR_IFACE, in_signature='a{sv}', out_signature='ay')
    def ReadValue(self, options):
        self.context.authorize(options)
        offset = int(options.get('offset', 0))
        if not 0 <= offset <= len(self.value):
            self.context.note('read_rejected', reason='invalid-offset')
            raise InvalidOffset('Offset exceeds current value length')
        self.context.note('read', role=self.role, offset=offset, length=len(self.value) - offset)
        return dbus.ByteArray(self.value[offset:])

    @dbus.service.method(CHAR_IFACE, in_signature='aya{sv}', out_signature='')
    def WriteValue(self, value, options):
        self.context.authorize(options)
        if self.role != 'rx':
            raise NotPermitted('TX is read and notify only')
        if int(options.get('offset', 0)) != 0:
            self.context.note('write_rejected', reason='nonzero-offset')
            raise NotSupported('Partial and offset writes are not supported')
        if bool(options.get('prepare-authorize', False)) or str(options.get('type', 'request')) != 'request':
            self.context.note('write_rejected', reason='unsupported-procedure')
            raise NotSupported('Only a complete Write Request is supported; no prepare or reliable write')
        value = bytes(value)
        try:
            seq = payload_sequence(value)
        except dbus.exceptions.DBusException:
            self.context.note('write_rejected', reason='invalid-challenge')
            raise
        mtu = int(options.get('mtu', 23))
        if mtu < len(value) + 3 or (len(value) == 47 and 'mtu' not in options):
            self.context.note('write_rejected', reason='mtu-too-small-or-missing')
            raise InvalidValueLength('Entire challenge must fit one negotiated ATT Write Request')
        if not self.context.tx.notifying:
            self.context.note('write_rejected', reason='not-subscribed')
            raise NotPermitted('Subscribe to TX notifications before writing RX')
        self.value = value
        self.context.tx.value = value
        self.context.note('accepted_write', sequence=seq, length=len(value), mtu=mtu,
                          sha256=hashlib.sha256(value).hexdigest())
        self.context.tx.PropertiesChanged(CHAR_IFACE, {'Value': dbus.ByteArray(value)}, [])
        self.context.note('notification_signal_emitted', sequence=seq, length=len(value))

    @dbus.service.method(CHAR_IFACE, in_signature='', out_signature='')
    def StartNotify(self):
        if self.role != 'tx':
            raise NotSupported('RX does not support notifications')
        if not self.context.accepting:
            raise NotPermitted('Test window is closed')
        if not self.notifying:
            self.notifying = True
            self.PropertiesChanged(CHAR_IFACE, {'Notifying': dbus.Boolean(True)}, [])
            self.context.note('notify_started')
        # Do not send READY here: only an accepted challenge emits Value.

    @dbus.service.method(CHAR_IFACE, in_signature='', out_signature='')
    def StopNotify(self):
        if self.role != 'tx':
            raise NotSupported('RX does not support notifications')
        if self.notifying:
            self.notifying = False
            self.PropertiesChanged(CHAR_IFACE, {'Notifying': dbus.Boolean(False)}, [])
            self.context.note('notify_stopped')


class Service(PropertyObject):
    def __init__(self, bus):
        super().__init__(bus, SERVICE_PATH, SERVICE_IFACE)

    def properties(self):
        return {'UUID': SERVICE_UUID, 'Primary': dbus.Boolean(True),
                'Characteristics': dbus.Array([dbus.ObjectPath(RX_PATH), dbus.ObjectPath(TX_PATH)], signature='o')}


class Application(dbus.service.Object):
    def __init__(self, bus, context):
        self.service = Service(bus)
        context.rx = Characteristic(bus, context, 'rx')
        context.tx = Characteristic(bus, context, 'tx')
        self.objects = [self.service, context.rx, context.tx]
        super().__init__(bus, ROOT)

    @dbus.service.method(OBJECT_MANAGER, in_signature='', out_signature='a{oa{sa{sv}}}')
    def GetManagedObjects(self):
        return {dbus.ObjectPath(obj.path): {obj.interface: obj.properties()} for obj in self.objects}

    def remove_all(self):
        errors = []
        for obj in reversed(self.objects):
            try:
                obj.remove_from_connection()
            except Exception as error:
                errors.append(str(error))
        try:
            self.remove_from_connection()
        except Exception as error:
            errors.append(str(error))
        if errors:
            raise RuntimeError('Application object removal: ' + '; '.join(errors))


class Advertisement(PropertyObject):
    def __init__(self, bus, context, seconds):
        self.context = context
        self.seconds = seconds
        super().__init__(bus, ADV_PATH, ADV_IFACE)

    def properties(self):
        return {'Type': 'peripheral', 'ServiceUUIDs': dbus.Array([SERVICE_UUID], signature='s'),
                'LocalName': 'RMXLE', 'Discoverable': dbus.Boolean(True),
                'Timeout': dbus.UInt16(self.seconds)}

    @dbus.service.method(ADV_IFACE, in_signature='', out_signature='')
    def Release(self):
        self.context.advertisement_registered = False
        self.context.note('advertisement_released')
        if not self.context.stopping:
            GLib.idle_add(self.context.stop, 'advertisement-released')


def key_fingerprint(root):
    """Hash existing key sections in RAM, never print or write the key material."""
    if not root.is_dir() or root.is_symlink():
        raise RuntimeError('Bluetooth storage must already exist as a real directory')
    records = []
    for info in sorted(root.glob('*/*/info')):
        if info.is_symlink():
            raise RuntimeError('Unexpected symlink in pairing storage')
        parser = configparser.RawConfigParser(interpolation=None, strict=True)
        parser.optionxform = str
        parser.read_string(info.read_text())
        for section in parser.sections():
            if 'key' in section.lower():
                records.append((str(info.relative_to(root)), section, sorted(parser.items(section))))
    for identity in sorted(root.glob('*/identity')):
        if identity.is_symlink():
            raise RuntimeError('Unexpected identity symlink')
        records.append((str(identity.relative_to(root)), 'local-identity', identity.read_bytes().hex()))
    raw = json.dumps(records, sort_keys=True, separators=(',', ':')).encode()
    return {'key_sections': len(records), 'sha256': hashlib.sha256(raw).hexdigest()}


def capture_child_setup():
    """Make the Linux btmon child receive SIGINT if its Python parent dies."""
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(1, signal.SIGINT, 0, 0, 0) != 0:  # PR_SET_PDEATHSIG
        os._exit(126)
    if os.getppid() == 1:
        os._exit(126)


class HCIAddress(ctypes.Structure):
    _fields_ = [('family', ctypes.c_ushort), ('index', ctypes.c_ushort), ('channel', ctypes.c_ushort)]


def open_native_monitor():
    """Reuse kernel130 open_channel(2): bind monitor only, never send commands."""
    monitor = socket.socket(31, socket.SOCK_RAW | socket.SOCK_CLOEXEC, 1)
    address = HCIAddress(31, 0xffff, 2)
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.bind(monitor.fileno(), ctypes.byref(address), ctypes.sizeof(address)):
        error = ctypes.get_errno()
        monitor.close()
        raise OSError(error, os.strerror(error))
    return monitor


class NativeMonitorCapture:
    """kernel185 packet.hex()+monotonic format, with bounded reader lifetime."""
    def __init__(self, path, socket_factory=open_native_monitor):
        self.monitor = self.log = self.thread = None
        self.stop_event = threading.Event()
        self.ready = threading.Event()
        self.error = None
        self.packet_count = 0
        self.closed = False
        try:
            self.monitor = socket_factory()
            self.monitor.settimeout(0.25)
            self.log = path.open('x', encoding='utf-8')
            self.thread = threading.Thread(target=self.read_packets, name='private-hci-monitor', daemon=True)
            self.thread.start()
            if not self.ready.wait(timeout=1) or not self.healthy():
                raise RuntimeError('Native HCI monitor reader did not start')
        except Exception:
            self.close()
            raise

    def read_packets(self):
        try:
            self.ready.set()
            while not self.stop_event.is_set():
                try:
                    packet = self.monitor.recv(65535)
                except TimeoutError:
                    continue
                except OSError:
                    if self.stop_event.is_set():
                        break
                    raise
                if not packet:
                    raise RuntimeError('Native HCI monitor reached EOF')
                self.log.write(json.dumps({'monotonic': time.monotonic(), 'packet': packet.hex()}) + '\n')
                self.log.flush()
                self.packet_count += 1
        except Exception as error:
            self.error = type(error).__name__ + ': ' + str(error)
        finally:
            try:
                self.log.close()
            except Exception as error:
                self.error = self.error or ('log-close: ' + type(error).__name__ + ': ' + str(error))

    def healthy(self):
        return self.thread is not None and self.thread.is_alive() and self.error is None and not self.closed

    def close(self):
        self.closed = True
        self.stop_event.set()
        errors = []
        if self.monitor is not None:
            try:
                self.monitor.close()
            except Exception as error:
                errors.append('socket close: ' + str(error))
        if self.thread is not None and self.thread.ident is not None:
            try:
                self.thread.join(timeout=1)
                if self.thread.is_alive():
                    errors.append('reader did not stop within one second')
            except Exception as error:
                errors.append('reader join: ' + str(error))
        elif self.log is not None:
            try:
                self.log.close()
            except Exception as error:
                errors.append('log close: ' + str(error))
        if errors:
            raise RuntimeError('Native HCI monitor cleanup: ' + '; '.join(errors))


def runtime_identity(args):
    """Read the handed-off identity immediately before any adapter mutation."""
    boot_id = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    guard_id = Path(args.boot_guard_file).read_text().strip()
    if not re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', boot_id):
        raise RuntimeError('Current boot ID is malformed')
    if guard_id != boot_id:
        raise RuntimeError('Current boot ID does not match the explicitly handed-off guard file')
    release = os.uname().release
    if release != EXPECTED_RELEASE:
        raise RuntimeError('Kernel release does not match the exact k363 target')
    compatible = Path('/sys/firmware/devicetree/base/compatible').read_bytes().split(b'\0')
    if b'realme,samurai' not in compatible:
        raise RuntimeError('Device compatible does not contain realme,samurai')
    manifest_sha256 = hashlib.sha256(CHARGING_MANIFEST.read_bytes()).hexdigest()
    if manifest_sha256 != args.charging_manifest_sha256:
        raise RuntimeError('Charging manifest differs from the explicit handoff SHA256')
    return {'boot_id_private': boot_id, 'guard_matches_boot': True,
            'release': release, 'compatible_contains_realme_samurai': True,
            'charging_manifest_sha256': manifest_sha256}


class PeerRun:
    def __init__(self, args):
        self.args = args
        self.accepting = False
        self.stopping = False
        self.cleanup_in_progress = False
        self.cleanup_complete = False
        self.cleanup_report = None
        self.cleanup_deadline = None
        self.cleanup_attempted = set()
        self.cleanup_results = {}
        self.cleanup_owner_ok = False
        self.advertisement_registered = False
        self.application_requested = False
        self.advertisement_requested = False
        self.application_registered = False
        self.deadline = time.monotonic() + args.seconds
        self.loop = GLib.MainLoop()
        self.control = self.export = self.app = self.advertisement = None
        self.owner = self.original = self.keys_before = self.capture = self.capture_log = None
        self.identity_before = None
        self.native_capture = None
        self.capture_backend = None
        self.events = []
        self.errors = []
        self.owned_adapter_mutations = []
        self.output = Path(args.output)
        if not self.output.is_absolute():
            raise ValueError('--output must be an absolute new private directory')
        self.output.mkdir(mode=0o700, parents=False, exist_ok=False)
        os.chmod(self.output, 0o700)
        self.events_file = (self.output / 'events-private.jsonl').open('x')
        self.exit_code = 1

    def note(self, event, **fields):
        record = dict(event=event, elapsed_ms=round((time.monotonic() - (self.deadline - self.args.seconds)) * 1000), **fields)
        self.events.append(record)
        self.events_file.write(json.dumps(record, sort_keys=True) + '\n')
        self.events_file.flush()

    def remaining(self):
        left = self.deadline - time.monotonic()
        if left <= 0:
            raise RuntimeError('Single test deadline expired')
        return min(left, 8.0)

    def proxy(self, path):
        return self.control.get_object(self.owner, path, introspect=False)

    def managed(self):
        return self.proxy('/').GetManagedObjects(dbus_interface=OBJECT_MANAGER, timeout=self.remaining())

    def adapter_properties(self, timeout=5):
        return self.proxy(self.args.adapter).GetAll(ADAPTER_IFACE, dbus_interface=PROPERTIES, timeout=timeout)

    def current_owner(self, timeout):
        return str(self.control.call_blocking('org.freedesktop.DBus', '/org/freedesktop/DBus',
                   'org.freedesktop.DBus', 'GetNameOwner', 's', ('org.bluez',), timeout=timeout))

    def same_owner(self, timeout):
        try:
            return self.current_owner(timeout) == self.owner
        except dbus.exceptions.DBusException:
            return False

    def set_adapter(self, name, value, timeout):
        if not self.stopping:
            self.require_capture()
        self.proxy(self.args.adapter).Set(ADAPTER_IFACE, name, dbus.Boolean(value, variant_level=1),
                                          dbus_interface=PROPERTIES, timeout=timeout)

    def authorize(self, options):
        if not self.accepting or time.monotonic() >= self.deadline:
            raise NotPermitted('Test window is closed')
        if self.args.offline_export:
            if str(options.get('device', '')) != OFFLINE_PEER:
                raise NotAuthorized('Offline fixture peer does not match')
            return
        try:
            self.require_capture()
        except Exception as error:
            self.errors.append(str(error))
            GLib.idle_add(self.stop, 'capture-exited')
            raise NotPermitted('HCI capture stopped; test writes and reads are closed')
        if str(options.get('link', 'LE')) != 'LE':
            raise NotAuthorized('Only the LE test link is allowed')
        path = str(options.get('device', ''))
        if not path.startswith(self.args.adapter + '/dev_'):
            raise NotAuthorized('Missing or foreign BlueZ peer object')
        props = self.proxy(path).GetAll(DEVICE_IFACE, dbus_interface=PROPERTIES, timeout=self.remaining())
        if str(props.get('Address', '')).upper() != self.args.peer_address:
            self.note('peer_rejected')
            raise NotAuthorized('Peer address does not match the explicitly supplied Windows adapter')

    def prepare(self):
        if self.args.offline_export:
            self.export = dbus.bus.BusConnection(self.args.bus_address)
            self.app = Application(self.export, self)
            self.advertisement = Advertisement(self.export, self, self.args.seconds)
            self.accepting = True
            print(json.dumps({'offline_unique_name': self.export.get_unique_name(), 'no_bluez_or_radio_access': True}), flush=True)
            return
        if os.geteuid() != 0:
            raise RuntimeError('Runtime mode requires root for private key verification and HCI capture')
        self.control = dbus.SystemBus(private=True)
        self.owner = self.current_owner(self.remaining())  # Bus daemon query never activates BlueZ.
        if not re.fullmatch(r':\d+\.\d+', self.owner):
            raise RuntimeError('BlueZ owner is not a unique bus name')
        objects = self.managed()
        interfaces = objects.get(dbus.ObjectPath(self.args.adapter), {})
        if not all(name in interfaces for name in (ADAPTER_IFACE, GATT_MANAGER, ADV_MANAGER)):
            raise RuntimeError('Requested adapter lacks GATT or advertising manager')
        adapter = interfaces[ADAPTER_IFACE]
        if bool(adapter.get('Discovering', False)):
            raise RuntimeError('Discovery already active; do not overlap another transaction')
        if any(bool(ifs.get(DEVICE_IFACE, {}).get('Connected', False)) for ifs in objects.values()):
            raise RuntimeError('A Bluetooth connection already exists; test requires an idle adapter')
        if int(interfaces[ADV_MANAGER].get('ActiveInstances', 0)) != 0:
            raise RuntimeError('Another LE advertisement is already active')
        names = ('Powered', 'Pairable', 'Discoverable', 'PairableTimeout', 'DiscoverableTimeout')
        self.original = {name: adapter[name] for name in names}
        self.keys_before = key_fingerprint(Path(self.args.storage))
        (self.output / 'keys-before-private.json').write_text(json.dumps(self.keys_before, indent=2) + '\n')
        (self.output / 'adapter-before-private.json').write_text(json.dumps({k: int(v) if 'Timeout' in k else bool(v) for k, v in self.original.items()}, indent=2) + '\n')
        btmon = shutil.which('btmon') if self.args.capture_backend != 'native-monitor' else None
        if self.args.capture_backend == 'btmon' and not btmon:
            raise RuntimeError('Explicit btmon backend is unavailable; no silent backend switch')
        if btmon:
            self.capture_backend = 'btmon'
            self.capture_log = (self.output / 'btmon-private.txt').open('xb')
            self.capture = subprocess.Popen([btmon, '-i', self.args.adapter.rsplit('/', 1)[1], '-w', str(self.output / 'capture-private.btsnoop')],
                                            stdin=subprocess.DEVNULL, stdout=self.capture_log, stderr=subprocess.STDOUT,
                                            start_new_session=True, preexec_fn=capture_child_setup)
        else:
            self.capture_backend = 'native-monitor'
            self.native_capture = NativeMonitorCapture(self.output / 'hci-monitor-private.jsonl')
        self.require_capture()
        self.note('capture_started', backend=self.capture_backend,
                  format='btsnoop-and-text' if btmon else 'native-monitor-jsonl')
        GLib.timeout_add(200, self.capture_health)
        # A host-side earlier SSH guard cannot authorize this native transaction.
        # A matching old boot ID is identity only, never a current-health claim.
        self.identity_before = runtime_identity(self.args)
        (self.output / 'identity-before-private.json').write_text(json.dumps(self.identity_before, indent=2) + '\n')
        self.note('runtime_identity_guard_verified')
        for name, value in [('Powered', True), ('Pairable', False), ('Discoverable', False)]:
            if bool(self.adapter_properties(timeout=self.remaining())[name]) != value:
                # Record before the call: even a timed-out Set may have taken effect.
                self.owned_adapter_mutations.append(name)
                self.set_adapter(name, value, self.remaining())
        if bool(self.adapter_properties(timeout=self.remaining())['Pairable']):
            raise RuntimeError('Adapter remains pairable')
        self.export = dbus.SystemBus(private=True)
        self.app = Application(self.export, self)
        self.advertisement = Advertisement(self.export, self, max(1, int(self.deadline - time.monotonic())))
        self.control.add_signal_receiver(self.owner_changed, signal_name='NameOwnerChanged', dbus_interface='org.freedesktop.DBus', arg0='org.bluez')
        self.require_capture()
        self.application_requested = True
        self.export.get_object(self.owner, self.args.adapter, introspect=False).RegisterApplication(
            dbus.ObjectPath(ROOT), dbus.Dictionary({}, signature='sv'), dbus_interface=GATT_MANAGER,
            reply_handler=self.application_ready, error_handler=self.registration_failed, timeout=self.remaining())

    def application_ready(self):
        self.application_registered = True
        if self.stopping:
            return
        try:
            self.require_capture()
            self.advertisement_requested = True
            self.export.get_object(self.owner, self.args.adapter, introspect=False).RegisterAdvertisement(
                dbus.ObjectPath(ADV_PATH), dbus.Dictionary({}, signature='sv'), dbus_interface=ADV_MANAGER,
                reply_handler=self.advertisement_ready, error_handler=self.registration_failed, timeout=self.remaining())
        except Exception as error:
            self.registration_failed(error)

    def advertisement_ready(self):
        self.advertisement_registered = True
        if time.monotonic() >= self.deadline and not self.stopping:
            self.stop('deadline-before-ready')
            return
        if not self.stopping:
            self.accepting = True
            self.note('gatt_and_advertisement_registered')
            print(json.dumps({'ready': True, 'service_uuid': SERVICE_UUID, 'local_name': 'RMXLE',
                              'capture_backend': self.capture_backend,
                              'capture_format': 'btsnoop-and-text' if self.capture_backend == 'btmon' else 'native-monitor-jsonl',
                              'remaining_seconds': max(0, round(self.deadline - time.monotonic(), 2))}), flush=True)

    def registration_failed(self, error):
        if not self.stopping:
            self.errors.append('registration: ' + str(error))
            self.stop('registration-failed')

    def owner_changed(self, name, old, new):
        if str(old) == self.owner and str(new) != self.owner and not self.stopping:
            self.errors.append('Pinned BlueZ owner disappeared; no daemon activation or retry')
            self.stop('bluez-owner-lost')

    def require_capture(self):
        if self.capture_backend == 'btmon' and self.capture and self.capture.poll() is None:
            return
        if self.capture_backend == 'native-monitor' and self.native_capture and self.native_capture.healthy():
            return
        detail = self.native_capture.error if self.native_capture else 'capture process unavailable or exited'
        raise RuntimeError('HCI capture is not healthy: ' + str(detail))

    def capture_health(self):
        if self.stopping:
            return False
        try:
            self.require_capture()
        except Exception as error:
            self.errors.append(str(error))
            self.stop('capture-exited')
            return False
        return True

    def cleanup_note(self, label, **fields):
        try:
            self.note(label, **fields)
        except Exception as error:
            self.errors.append('cleanup-log ' + label + ': ' + str(error))

    def cleanup_call(self, label, function, allow_absent=False, log=True):
        """Attempt each action once; diagnostic failure cannot undo its result."""
        if label in self.cleanup_attempted:
            return self.cleanup_results.get(label, False)
        self.cleanup_attempted.add(label)
        succeeded = False
        absent = False
        try:
            function()
            succeeded = True
        except dbus.exceptions.DBusException as error:
            absent = allow_absent and error.get_dbus_name() == 'org.bluez.Error.DoesNotExist'
            succeeded = absent
            if not absent:
                self.errors.append(label + ': ' + str(error))
        except Exception as error:
            self.errors.append(label + ': ' + str(error))
        self.cleanup_results[label] = succeeded
        if log:
            self.cleanup_note(label, succeeded=succeeded, already_absent=absent)
        return succeeded

    def stop(self, reason):
        if self.cleanup_complete or self.cleanup_in_progress:
            return False
        self.stopping = True
        self.accepting = False
        self.cleanup_in_progress = True
        if self.cleanup_deadline is None:
            self.cleanup_deadline = time.monotonic() + 30
        if self.cleanup_report is None:
            self.cleanup_report = {
                'mode': 'offline-export' if self.args.offline_export else 'phone-peripheral',
                'stop_reason': reason, 'errors': self.errors,
                'cleanup': {'private_bus_closed': False, 'adapter_restored': None, 'keys_unchanged': None,
                            'known_peer_disconnected': None, 'advertisement_instances_restored': None,
                            'runtime_identity_unchanged': None}}
        report = self.cleanup_report
        cleanup = report['cleanup']

        def cleanup_timeout():
            left = self.cleanup_deadline - time.monotonic()
            if left <= 0:
                raise RuntimeError('Single 30-second D-Bus cleanup deadline expired')
            return min(3, left)

        def verify_owner():
            if self.current_owner(cleanup_timeout()) != self.owner:
                raise RuntimeError('Pinned BlueZ owner is absent or replaced; no state writes')
            self.cleanup_owner_ok = True

        def export_proxy():
            return self.export.get_object(self.owner, self.args.adapter, introspect=False)

        def disconnect_peer():
            objects = self.proxy('/').GetManagedObjects(dbus_interface=OBJECT_MANAGER, timeout=cleanup_timeout())
            for path, interfaces in objects.items():
                device = interfaces.get(DEVICE_IFACE, {})
                if str(path).startswith(self.args.adapter + '/dev_') and str(device.get('Address', '')).upper() == self.args.peer_address and bool(device.get('Connected', False)):
                    self.cleanup_call('disconnect_explicit_peer_' + str(path), lambda path=path: self.proxy(str(path)).Disconnect(
                        dbus_interface=DEVICE_IFACE, timeout=cleanup_timeout()))

        def verify_peer():
            objects = self.proxy('/').GetManagedObjects(dbus_interface=OBJECT_MANAGER, timeout=cleanup_timeout())
            cleanup['known_peer_disconnected'] = not any(
                str(path).startswith(self.args.adapter + '/dev_') and
                str(i.get(DEVICE_IFACE, {}).get('Address', '')).upper() == self.args.peer_address and
                bool(i.get(DEVICE_IFACE, {}).get('Connected', False)) for path, i in objects.items())
            if not cleanup['known_peer_disconnected']:
                raise RuntimeError('Explicit peer remains connected')

        def verify_adapter():
            after = self.adapter_properties(timeout=cleanup_timeout())
            cleanup['adapter_restored'] = all(after[name] == value for name, value in self.original.items())
            if not cleanup['adapter_restored']:
                raise RuntimeError('Adapter properties differ from original values')

        def verify_advertisements():
            manager = self.proxy(self.args.adapter).GetAll(ADV_MANAGER, dbus_interface=PROPERTIES, timeout=cleanup_timeout())
            cleanup['advertisement_instances_restored'] = int(manager.get('ActiveInstances', -1)) == 0
            if not cleanup['advertisement_instances_restored']:
                raise RuntimeError('Advertisement instances remain active or unknown')

        def verify_keys():
            after_keys = key_fingerprint(Path(self.args.storage))
            cleanup['keys_unchanged'] = after_keys == self.keys_before
            self.cleanup_call('save_keys_after', lambda: (self.output / 'keys-after-private.json').write_text(
                json.dumps(after_keys, indent=2) + '\n'))
            if not cleanup['keys_unchanged']:
                raise RuntimeError('Pairing keys changed; no blind overwrite of key material')

        def verify_identity():
            identity_after = runtime_identity(self.args)
            cleanup['runtime_identity_unchanged'] = identity_after == self.identity_before
            self.cleanup_call('save_identity_after', lambda: (self.output / 'identity-after-private.json').write_text(
                json.dumps(identity_after, indent=2) + '\n'))
            if not cleanup['runtime_identity_unchanged']:
                raise RuntimeError('Runtime identity changed during the test')

        def stop_btmon():
            status = {'running': True}
            self.cleanup_call('poll_btmon', lambda: status.update(running=self.capture.poll() is None))
            if status['running']:
                graceful = self.cleanup_call('signal_btmon', lambda: self.capture.send_signal(signal.SIGINT))
                if graceful:
                    graceful = self.cleanup_call('wait_btmon', lambda: self.capture.wait(timeout=3))
                if not graceful:
                    self.cleanup_call('kill_btmon', lambda: self.capture.kill())
                    self.cleanup_call('reap_btmon', lambda: self.capture.wait(timeout=2))
            cleanup['btmon_exit_code'] = self.capture.returncode
            if self.capture.returncode is None:
                raise RuntimeError('Owned btmon child did not reach terminal status')

        core_attempted = False
        try:
            self.cleanup_note('stopping', reason=reason)
            if self.control and self.owner:
                self.cleanup_call('verify_bluez_owner', verify_owner)
            if self.export:
                if self.cleanup_owner_ok:
                    if self.advertisement_requested:
                        self.cleanup_call('unregister_advertisement', lambda: export_proxy().UnregisterAdvertisement(
                            dbus.ObjectPath(ADV_PATH), dbus_interface=ADV_MANAGER, timeout=cleanup_timeout()), allow_absent=True)
                    if self.application_requested:
                        self.cleanup_call('unregister_application', lambda: export_proxy().UnregisterApplication(
                            dbus.ObjectPath(ROOT), dbus_interface=GATT_MANAGER, timeout=cleanup_timeout()), allow_absent=True)
                elif self.application_requested or self.advertisement_requested:
                    self.errors.append('Cannot explicitly unregister: pinned BlueZ owner is unconfirmed')
                if self.advertisement:
                    self.cleanup_call('remove_advertisement_object', lambda: self.advertisement.remove_from_connection())
                if self.app:
                    self.cleanup_call('remove_application_objects', lambda: self.app.remove_all())
                cleanup['private_bus_closed'] = self.cleanup_call('close_private_bus', lambda: self.export.close())
                if cleanup['private_bus_closed']:
                    self.export = None
            if self.original is not None and self.identity_before is not None:
                cleanup['adapter_restored'] = False
                cleanup['known_peer_disconnected'] = False
                cleanup['advertisement_instances_restored'] = False
                if not self.cleanup_owner_ok:
                    self.errors.append('Cannot restore original adapter: pinned BlueZ owner is unconfirmed')
                else:
                    self.cleanup_call('disconnect_known_peer', disconnect_peer)
                    self.cleanup_call('verify_peer_disconnected', verify_peer)
                    for name in ('Discoverable', 'Pairable', 'Powered'):
                        if name in self.owned_adapter_mutations:
                            self.cleanup_call('restore_adapter_' + name, lambda name=name: self.set_adapter(
                                name, bool(self.original[name]), cleanup_timeout()))
                    self.cleanup_call('verify_adapter_restored', verify_adapter)
                    self.cleanup_call('verify_advertisements_removed', verify_advertisements)
            if self.keys_before is not None:
                cleanup['keys_unchanged'] = False
                self.cleanup_call('verify_keys_unchanged', verify_keys)
            if self.identity_before is not None:
                cleanup['runtime_identity_unchanged'] = False
                self.cleanup_call('verify_runtime_identity', verify_identity)
            core_attempted = True
        except Exception as error:
            self.errors.append('unexpected-cleanup: ' + str(error))
        finally:
            # These remain independent even if an earlier diagnostic or callback failed.
            try:
                if self.capture:
                    self.cleanup_call('stop_btmon', stop_btmon)
                if self.capture_log:
                    self.cleanup_call('close_capture_log', lambda: self.capture_log.close())
                if self.native_capture:
                    cleanup['native_monitor_closed'] = self.cleanup_call('close_native_monitor', lambda: self.native_capture.close())
                    def inspect_native_capture():
                        cleanup['native_monitor_reader_stopped'] = not self.native_capture.thread.is_alive()
                        cleanup['native_monitor_packet_count'] = self.native_capture.packet_count
                        if not cleanup['native_monitor_reader_stopped'] or self.native_capture.error:
                            raise RuntimeError('Native monitor reader/error: ' + str(self.native_capture.error))
                    self.cleanup_call('verify_native_monitor_stopped', inspect_native_capture)
                if self.control:
                    cleanup['control_bus_closed'] = self.cleanup_call('close_control_bus', lambda: self.control.close())
                    if cleanup['control_bus_closed']:
                        self.control = None
                cleanup['events_file_closed'] = self.cleanup_call('close_events_file', lambda: self.events_file.close(), log=False)
                cleanup['loop_quit_succeeded'] = self.cleanup_call('quit_loop', lambda: self.loop.quit(), log=False)
                report.update(accepted_writes=[x for x in self.events if x['event'] == 'accepted_write'],
                              notification_signals_emitted=sum(x['event'] == 'notification_signal_emitted' for x in self.events),
                              central_must_verify_complete_challenges=True, full_le_hardware_pass_claimed=False,
                              no_pair_trust_or_key_write_calls=True,
                              native_runtime_identity_guard_verified=self.identity_before is not None,
                              guard_proves_identity_not_current_health=True, capture_backend=self.capture_backend,
                              capture_format='btsnoop-and-text' if self.capture_backend == 'btmon' else
                              'native-monitor-jsonl' if self.capture_backend else None,
                              cleanup_actions_finished=core_attempted)
                self.cleanup_call('emit_terminal_stdout', lambda: print(json.dumps({
                    'finished': True, 'error_count': len(self.errors), 'cleanup': cleanup,
                    'capture_backend': self.capture_backend, 'capture_format': report['capture_format'],
                    'accepted_write_count': len(report['accepted_writes']),
                    'full_le_hardware_pass_claimed': False}), flush=True), log=False)
                self.cleanup_call('write_summary', lambda: (self.output / 'summary-private.json').write_text(
                    json.dumps(report, indent=2) + '\n'), log=False)
            finally:
                self.cleanup_in_progress = False
                self.cleanup_complete = core_attempted
                self.exit_code = 0 if self.cleanup_complete and not self.errors else 1
        return False


    def run(self):
        GLib.timeout_add(max(1, int((self.deadline - time.monotonic()) * 1000)), self.stop, 'deadline')
        for sig in (signal.SIGTERM, signal.SIGINT):
            GLibUnix.signal_add(GLib.PRIORITY_DEFAULT, sig, self.stop, 'signal-' + str(sig))
        try:
            self.prepare()
            if not self.stopping:
                self.loop.run()
        except Exception as error:
            self.errors.append('setup-or-loop: ' + str(error))
        finally:
            if not self.cleanup_complete:
                self.stop('exception-or-loop-exit')
        return self.exit_code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, help='New absolute private directory; parent must exist')
    parser.add_argument('--seconds', type=int, default=60, help='One deadline for setup and serving, 10..180 seconds')
    parser.add_argument('--adapter', default='/org/bluez/hci0')
    parser.add_argument('--peer-address', help='Explicit Windows adapter BluetoothAddress; never logged publicly')
    parser.add_argument('--boot-guard-file', help='Explicit absolute file containing the current handed-off boot ID')
    parser.add_argument('--charging-manifest-sha256', help='Explicit SHA256 of the current handed-off charging manifest')
    parser.add_argument('--storage', default='/var/lib/bluetooth')
    parser.add_argument('--capture-backend', choices=('auto', 'btmon', 'native-monitor'), default='auto',
                        help='auto prefers btmon and uses read-only native HCI monitor only if btmon is missing')
    parser.add_argument('--offline-export', action='store_true', help='Export API objects only on a supplied private session bus')
    parser.add_argument('--bus-address', help='Required only for offline-export; never used in runtime mode')
    args = parser.parse_args()
    if not 10 <= args.seconds <= 180 or not re.fullmatch(r'/org/bluez/hci\d+', args.adapter):
        parser.error('Invalid deadline or adapter path')
    if args.offline_export:
        if not args.bus_address or args.peer_address or args.boot_guard_file or args.charging_manifest_sha256 or args.capture_backend != 'auto':
            parser.error('offline-export requires --bus-address and does not accept runtime peer or identity arguments')
    elif args.bus_address or not args.peer_address or not re.fullmatch(r'(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}', args.peer_address):
        parser.error('Runtime requires an explicit peer address and no custom bus address')
    elif not args.boot_guard_file or not Path(args.boot_guard_file).is_absolute() or not args.charging_manifest_sha256 or not re.fullmatch(r'[0-9a-fA-F]{64}', args.charging_manifest_sha256):
        parser.error('Runtime requires --boot-guard-file absolute path and --charging-manifest-sha256 from the current handoff')
    if args.peer_address:
        args.peer_address = args.peer_address.upper()
    if args.charging_manifest_sha256:
        args.charging_manifest_sha256 = args.charging_manifest_sha256.lower()
    os.umask(0o077)
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    try:
        return PeerRun(args).run()
    except Exception as error:
        print(json.dumps({'setup_failed': type(error).__name__, 'message': str(error)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
