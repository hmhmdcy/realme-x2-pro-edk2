#!/usr/bin/python3
"""Maintain GNSS UTC and current global XTRA data without starting location sessions."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import urllib.parse
import urllib.request


def validity_current(start, hours, now):
    return 0 < hours <= 65535 and start <= now < start + hours * 3600


def tls_url(server):
    value = urllib.parse.urlsplit(server)
    if value.scheme not in ('http', 'https') or not value.hostname:
        raise ValueError('Invalid assistance server')
    if value.username or value.password or value.query or value.fragment:
        raise ValueError('Assistance URL must not carry credentials or query data')
    return urllib.parse.urlunsplit(('https', value.netloc, value.path, '', ''))


def validate_payload(data, rejected, now):
    if not data or len(data) > 5 * 1024 * 1024 or data.lstrip().lower().startswith((b'<html', b'<!doctype')):
        raise ValueError('Invalid assistance payload')
    digest = hashlib.sha256(data).hexdigest()
    previous = rejected.get(digest)
    if previous and not validity_current(previous['start'], previous['hours'], now):
        raise ValueError('Previously received data is still outside its validity window')
    return digest


class HttpsOnlyRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, newurl):
        target = urllib.parse.urlsplit(newurl)
        if target.scheme != 'https':
            raise ValueError('Assistance redirect must remain HTTPS')
        tls_url(newurl)
        return super().redirect_request(request, response, code, message, headers, newurl)


def loc_exchange(kind):
    """Connect before sending; wait for both ACK and indication, then release CID."""
    import gi
    gi.require_version('Qmi', '1.0')
    gi.require_version('Qrtr', '1.0')
    from gi.repository import Qmi, Qrtr, GLib, Gio
    assert kind in ('validity', 'utc')
    loop = GLib.MainLoop()
    cancel = Gio.Cancellable()
    state = {'kind': kind, 'ack': False, 'indication': False, 'errors': []}
    objects = {'device': None, 'client': None, 'bus': None, 'pending': True,
               'closing': False, 'cleanup': False, 'signal': None}
    timers = []

    def end():
        loop.quit()
        return False

    def closed(source, result, *_args):
        try:
            state['device_closed'] = bool(source.close_finish(result))
        except Exception as error:
            state['errors'].append(type(error).__name__)
        end()

    def released(source, result, *_args):
        try:
            state['client_released'] = bool(source.release_client_finish(result))
        except Exception as error:
            state['errors'].append(type(error).__name__)
        source.close_async(10, None, closed, None)

    def cleanup():
        objects['closing'] = True
        if objects['pending'] or objects['cleanup']:
            return
        objects['cleanup'] = True
        client, device = objects['client'], objects['device']
        if client is not None and objects['signal'] is not None:
            client.disconnect(objects['signal'])
        if client is not None:
            device.release_client(client, Qmi.DeviceReleaseClientFlags.RELEASE_CID,
                                  10, None, released, None)
        elif device is not None:
            device.close_async(10, None, closed, None)
        else:
            end()

    def callback(function):
        def wrapped(*args):
            objects['pending'] = False
            try:
                function(*args)
            except Exception as error:
                state['errors'].append(type(error).__name__)
                cleanup()
        return wrapped

    def complete():
        if state['ack'] and state['indication']:
            cleanup()

    def indication(_client, output):
        try:
            if int(output.get_indication_status()) != 0:
                raise RuntimeError('Unsuccessful LOC indication')
            if kind == 'validity':
                start, hours = output.get_validity_info()
                state.update(start=int(start), hours=int(hours))
            state['indication'] = True
            complete()
        except Exception as error:
            state['errors'].append(type(error).__name__)
            cleanup()

    @callback
    def acknowledged(source, result, *_args):
        method = ('get_predicted_orbits_data_validity_finish' if kind == 'validity'
                  else 'inject_utc_time_finish')
        output = getattr(source, method)(result)
        output.get_result()
        state['ack'] = True
        if objects['closing']:
            cleanup()
        else:
            complete()

    @callback
    def allocated(source, result, *_args):
        client = objects['client'] = source.allocate_client_finish(result)
        if objects['closing']:
            cleanup()
            return
        name = 'get-predicted-orbits-data-validity' if kind == 'validity' else 'inject-utc-time'
        objects['signal'] = client.connect(name, indication)
        objects['pending'] = True
        if kind == 'validity':
            client.get_predicted_orbits_data_validity(None, 10, cancel, acknowledged, None)
        else:
            request = Qmi.MessageLocInjectUtcTimeInput.new()
            request.set_utc_time(GLib.get_real_time() // 1000)
            request.set_time_uncertainty(1000)
            request.set_time_source(Qmi.LocInjectedTimeSource.UNKNOWN)
            client.inject_utc_time(request, 10, cancel, acknowledged, None)

    @callback
    def opened(source, result, *_args):
        if not source.open_finish(result):
            raise RuntimeError('LOC device open failed')
        if objects['closing']:
            cleanup()
            return
        objects['pending'] = True
        source.allocate_client(Qmi.Service.LOC, Qmi.CID_NONE, 10, cancel, allocated, None)

    @callback
    def ready(source, result, *_args):
        device = objects['device'] = Qmi.Device.new_from_node_finish(result)
        if objects['closing']:
            cleanup()
            return
        objects['pending'] = True
        device.open(Qmi.DeviceOpenFlags.EXPECT_INDICATIONS, 10, cancel, opened, None)

    @callback
    def bus_ready(source, result, *_args):
        bus = objects['bus'] = Qrtr.Bus.new_finish(result)
        if objects['closing']:
            cleanup()
            return
        node = bus.get_node(0)
        if node is None:
            raise RuntimeError('No modem QRTR node')
        objects['pending'] = True
        Qmi.Device.new_from_node(node, cancel, ready, None)

    def expired():
        state['errors'].append('deadline')
        objects['closing'] = True
        cancel.cancel()
        cleanup()
        return False

    def cleanup_expired():
        state['errors'].append('cleanup deadline')
        end()
        return False

    timers.append(GLib.timeout_add_seconds(35, expired))
    timers.append(GLib.timeout_add_seconds(65, cleanup_expired))
    Qrtr.Bus.new(2000, cancel, bus_ready, None)
    loop.run()
    for timer in timers:
        if GLib.MainContext.default().find_source_by_id(timer) is not None:
            GLib.source_remove(timer)
    if not (state['ack'] and state['indication'] and state.get('client_released')
            and state.get('device_closed') and not state['errors']):
        raise RuntimeError('LOC request or cleanup failed: ' + json.dumps(state))
    return state


def refresh_data(before, servers, query, download, inject, still_allowed, now):
    """Use firmware's absolute validity window, never duration alone."""
    if validity_current(before['start'], before['hours'], now()):
        return {'status': 'current', 'start': before['start'], 'hours': before['hours'],
                'download_count': 0, 'injection_count': 0}
    attempted = []
    for index, server in enumerate(servers):
        try:
            data = download(tls_url(str(server)), index)
            if not still_allowed():
                return {'status': 'inactive', 'download_count': len(attempted) + 1,
                        'injection_count': 0}
            inject(data)
            after = query()
            if not validity_current(after['start'], after['hours'], now()):
                return {'status': 'not-current-after-injection', 'download_count': len(attempted) + 1,
                        'injection_count': 1, 'start': after['start'], 'hours': after['hours']}
            return {'status': 'refreshed', 'download_count': len(attempted) + 1,
                    'injection_count': 1, 'start': after['start'], 'hours': after['hours']}
        except (OSError, ValueError) as error:
            attempted.append({'server_index': index, 'error_type': type(error).__name__})
    return {'status': 'download-failed', 'attempts': attempted,
            'download_count': len(attempted), 'injection_count': 0}


def run_once(directory, active_only=False, prepare_only=False):
    import dbus
    assert os.getuid() == 0
    assert b'realme,samurai\0' in Path('/sys/firmware/devicetree/base/compatible').read_bytes()
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    assert directory.stat().st_uid == 0 and directory.stat().st_mode & 0o077 == 0
    lock = (directory / 'worker.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    bus = dbus.SystemBus(private=True)
    try:
        service = 'org.freedesktop.ModemManager1'
        interface = service + '.Modem.Location'
        daemon = dbus.Interface(bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus'),
                                'org.freedesktop.DBus')
        owner = str(daemon.GetNameOwner(service))
        objects = dbus.Interface(bus.get_object(service, '/org/freedesktop/ModemManager1'),
                                 'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
        candidates = [path for path, values in objects.items()
                      if interface in values and int(values[interface]['SupportedAssistanceData']) & 1]
        if len(candidates) != 1:
            return {'status': 'no-unique-supported-modem'}
        obj = bus.get_object(service, candidates[0])
        props = dbus.Interface(obj, 'org.freedesktop.DBus.Properties')
        api = dbus.Interface(obj, interface)
    
        def allowed():
            return (str(daemon.GetNameOwner(service)) == owner
                    and (not bool(int(props.Get(interface, 'Enabled')) & 6) if prepare_only
                         else not active_only or bool(int(props.Get(interface, 'Enabled')) & 6)))
    
        if not allowed():
            return {'status': 'inactive'}
        tracking = subprocess.run(['/usr/bin/chronyc', '-n', 'tracking'],
                                  capture_output=True, timeout=10)
        if tracking.returncode != 0 or b'Leap status     : Normal' not in tracking.stdout:
            return {'status': 'clock-not-synchronized'}
        if not allowed():
            return {'status': 'inactive'}
        utc = loc_exchange('utc')
        if prepare_only:
            # Seed UTC before the first MM GPS session. A concurrent application
            # may win this race: record it instead of restarting its GPS session.
            owner_unchanged = str(daemon.GetNameOwner(service)) == owner
            gps_raced = bool(int(props.Get(interface, 'Enabled')) & 6)
            result = {'status': 'time-prepared' if owner_unchanged and not gps_raced
                      else 'time-preparation-raced',
                      'gps_inactive_before_send': True,
                      'gps_activity_raced': gps_raced,
                      'utc_ack_and_completion': utc['ack'] and utc['indication'],
                      'qmi_clients_released_and_closed': True,
                      'modem_owner_unchanged': owner_unchanged,
                      'download_count': 0, 'injection_count': 0,
                      'engine_start_sent': False, 'power_state_changed': False}
            (directory / 'time-preparation-result.json').write_text(json.dumps(result, indent=2) + '\n')
            return result
        before = loc_exchange('validity')
        servers = props.Get(interface, 'AssistanceDataServers')
        rejected_file = directory / 'rejected-payloads.json'
        rejected = json.loads(rejected_file.read_text()) if rejected_file.exists() else {}
        last_injected = None
    
        def download(url, index):
            request = urllib.request.Request(url, headers={'Cache-Control': 'no-cache',
                                                           'Pragma': 'no-cache'})
            opener = urllib.request.build_opener(HttpsOnlyRedirect())
            with opener.open(request, timeout=25) as response:
                final = urllib.parse.urlsplit(response.url)
                if final.scheme != 'https' or final.username or final.password or final.query or final.fragment:
                    raise ValueError('Unexpected redirect')
                data = response.read(5 * 1024 * 1024 + 1)
            validate_payload(data, rejected, time.time())
            (directory / ('candidate-' + str(index) + '.bin')).write_bytes(data)
            return data

        def inject(data):
            nonlocal last_injected
            api.InjectAssistanceData(dbus.ByteArray(data), timeout=120)
            last_injected = hashlib.sha256(data).hexdigest()

        def query_after_injection():
            time.sleep(1)
            return loc_exchange('validity')
    
        result = refresh_data(before, servers, query_after_injection, download, inject,
                              allowed, time.time)
        if result['status'] == 'not-current-after-injection' and last_injected:
            rejected[last_injected] = {'start': result['start'], 'hours': result['hours']}
            rejected_file.write_text(json.dumps(rejected, indent=2) + '\n')
        result['utc_ack_and_completion'] = utc['ack'] and utc['indication']
        result['validity_before'] = {'start': before['start'], 'hours': before['hours']}
        result['qmi_clients_released_and_closed'] = True
        result['engine_start_sent'] = False
        result['power_state_changed'] = False
        result['modem_owner_unchanged'] = str(daemon.GetNameOwner(service)) == owner
        if not result['modem_owner_unchanged']:
            result['status'] = 'modem-owner-changed'
        (directory / 'last-result.json').write_text(json.dumps(result, indent=2) + '\n')
        return result
    finally:
        bus.close()
        lock.close()


def retry_seconds(result):
    if result.get('status') in ('current', 'refreshed'):
        return 3600
    if result.get('status') == 'clock-not-synchronized':
        return 10
    if result.get('status') in ('time-preparation-raced', 'modem-owner-changed', 'inactive'):
        return 10
    return 600


class GnssPowerPolicy:
    """Own only power changes made for GNSS on a SIM-missing RMX1931.

    OFFLINE is an explicit user state and is never resumed or used for cleanup.
    This firmware accepts SHUTTING_DOWN -> ONLINE and ONLINE <-> LOW_POWER;
    OFFLINE -> ONLINE/LOW_POWER was rejected on the device.
    """

    def __init__(self, supported):
        self.supported = supported
        self.generation = None
        self.owned = False
        self.blocked = False
        self.failed_request = None
        self.state = {'owned': False, 'online_requests': 0, 'low_requests': 0,
                      'last_result': 'idle'}

    def eligible(self, value):
        return (self.supported and value['state'] == -1
                and value['failure'] == 2 and value['sim_absent'])

    def update(self, read, set_power, read_mode):
        value = read()
        if value['generation'] != self.generation:
            self.generation = value['generation']
            self.owned = self.blocked = False
            self.failed_request = None
        active = bool(value['enabled'] & 6)
        if not active:
            self.blocked = False
        if self.owned and (value['power'] != 3 or not self.eligible(value)):
            self.owned = False
            self.blocked = active
            self.state['last_result'] = 'external-power-or-modem-change'
        if not self.eligible(value):
            self.state['owned'] = self.owned
            return
        target = None
        if active and not self.blocked and value['power'] in (1, 2):
            request = (self.generation, 3, value['power'])
            if request == self.failed_request:
                return
            if value['power'] == 1:
                mode = read_mode()
                if mode != 'shutting-down':
                    self.state['last_result'] = ('offline-preserved' if mode == 'offline'
                                                 else 'initial-mode-not-resumable')
                    self.blocked = True
                    return
                # The GET may take time; do not turn on a stopped or replaced modem.
                current = read()
                if (current['generation'] != self.generation
                        or not self.eligible(current) or not current['enabled'] & 6
                        or current['power'] != value['power']):
                    self.state['last_result'] = 'request-changed-during-mode-query'
                    return
            target = 3
        elif not active and self.owned and value['power'] == 3:
            target = 2
        if target is None:
            self.state['owned'] = self.owned
            return
        request = (self.generation, target, value['power'])
        if request == self.failed_request:
            return
        self.state['online_requests' if target == 3 else 'low_requests'] += 1
        try:
            after = set_power(target)
        except Exception as error:
            self.failed_request = request
            self.state['last_result'] = 'power-request-failed'
            self.state['error_type'] = type(error).__name__
            self.state['owned'] = self.owned
            return
        if after['generation'] != self.generation or after['power'] != target:
            self.failed_request = request
            self.owned = False
            self.state['last_result'] = 'power-request-unconfirmed'
            self.state['owned'] = False
            return
        self.owned = target == 3
        self.failed_request = None
        self.state.pop('error_type', None)
        self.state.update(owned=self.owned,
                          last_result='online-for-gnss' if self.owned else 'idle-low-power')
        # A short-lived client can disappear while SetPowerState is in flight.
        if self.owned and not after['enabled'] & 6:
            self.update(read, set_power, read_mode)


def dms_operating_mode():
    """Read only the enum; do not log qmicli output or modem identifiers."""
    import re
    result = subprocess.run(['qmicli', '-p', '-d', 'qrtr://0',
                             '--dms-get-operating-mode'], capture_output=True,
                            text=True, timeout=20, env={**os.environ, 'LC_ALL': 'C'})
    match = re.search(r"Mode:\s*'([^']+)'", result.stdout)
    return match.group(1) if result.returncode == 0 and match else None


def watch(directory):
    """Prepare UTC once per MM owner while idle; refresh data only for active GPS."""
    import dbus
    assert os.getuid() == 0
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    assert directory.stat().st_uid == 0 and directory.stat().st_mode & 0o077 == 0
    bus = dbus.SystemBus(private=True)
    daemon = dbus.Interface(bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus'),
                            'org.freedesktop.DBus')
    service = 'org.freedesktop.ModemManager1'
    interface = service + '.Modem.Location'
    state = {'running': True, 'active': False, 'worker_starts': 0,
             'worker_completions': 0, 'last_result': None,
             'time_prepared': False, 'time_preparation_starts': 0,
             'time_preparation_completions': 0, 'time_preparation_last_result': None,
             'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    stopping = False
    child = None
    streams = []
    owner = None
    props = None
    modem_api = None
    modem_path = None
    modem_interface = service + '.Modem'
    compatible = Path('/proc/device-tree/compatible')
    supported = (compatible.exists()
                 and b'realme,samurai' in compatible.read_bytes().split(b'\0'))
    power = GnssPowerPolicy(supported)
    due = 0.0
    discover_due = 0.0
    preparation_due = 0.0
    child_kind = None
    child_owner = None

    def save():
        temporary = directory / 'watch-state.new'
        temporary.write_text(json.dumps(state, indent=2) + '\n')
        temporary.replace(directory / 'watch-state.json')

    def stop(_signum, _frame):
        nonlocal stopping
        stopping = True

    def power_snapshot():
        if str(daemon.GetNameOwner(service)) != owner:
            raise RuntimeError('Modem owner changed')
        modem = props.GetAll(modem_interface)
        return {'generation': (owner, modem_path),
                'state': int(modem['State']), 'failure': int(modem['StateFailedReason']),
                'sim_absent': str(modem['Sim']) == '/', 'power': int(modem['PowerState']),
                'enabled': int(props.Get(interface, 'Enabled'))}

    def set_power(value):
        modem_api.SetPowerState(dbus.UInt32(value), timeout=35)
        return power_snapshot()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    save()
    try:
        while not stopping:
            if child is not None and child.poll() is not None:
                for stream in streams:
                    stream.close()
                streams = []
                is_preparation = child_kind == 'prepare-time'
                prefix = 'time_preparation' if is_preparation else 'worker'
                state[prefix + '_completions'] += 1
                result_path = 'prepare-time-stdout-private.json' if is_preparation else 'worker-stdout-private.json'
                try:
                    result = json.loads((directory / result_path).read_text())
                except (ValueError, OSError):
                    result = {'status': 'worker-failed', 'exit': child.returncode}
                stale_owner = child_owner != owner
                if stale_owner:
                    result = {'status': 'modem-owner-changed'}
                if is_preparation:
                    state['time_preparation_last_result'] = result
                    state['time_prepared'] = result.get('status') == 'time-prepared'
                    preparation_due = 0.0 if stale_owner else time.monotonic() + retry_seconds(result)
                else:
                    state['last_result'] = result
                    due = 0.0 if stale_owner else time.monotonic() + retry_seconds(result)
                child = None
                save()
            try:
                current_owner = str(daemon.GetNameOwner(service)) if bus.name_has_owner(service) else None
                if current_owner != owner:
                    owner, props, discover_due = current_owner, None, 0
                    modem_api = modem_path = None
                    state['time_prepared'] = False
                    preparation_due = 0.0
                    due = 0.0
                    save()
                if owner is not None and props is None and time.monotonic() >= discover_due:
                    values = dbus.Interface(bus.get_object(service, '/org/freedesktop/ModemManager1'),
                                            'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
                    paths = [path for path, interfaces in values.items()
                             if interface in interfaces
                             and int(interfaces[interface]['SupportedAssistanceData']) & 1]
                    if len(paths) == 1:
                        modem_path = paths[0]
                        # Pin writes to the discovered unique owner, never its replacement.
                        modem_object = bus.get_object(owner, modem_path)
                        props = dbus.Interface(modem_object,
                                               'org.freedesktop.DBus.Properties')
                        modem_api = dbus.Interface(modem_object, modem_interface)
                    discover_due = time.monotonic() + 30
                active = bool(int(props.Get(interface, 'Enabled')) & 6) if props else False
                newly_active = active and not state['active']
                if active != state['active']:
                    state['active'] = active
                    save()
                if props is not None:
                    previous_power_state = dict(power.state)
                    power.update(power_snapshot, set_power, dms_operating_mode)
                    state['power_policy'] = dict(power.state)
                    if power.state != previous_power_state:
                        save()
                prepare = (props is not None and not active and not state['time_prepared']
                           and time.monotonic() >= preparation_due)
                assist = active and (newly_active or time.monotonic() >= due)
                if child is None and (prepare or assist):
                    child_kind = 'prepare-time' if prepare else 'worker'
                    child_owner = owner
                    stdout = (directory / (child_kind + '-stdout-private.json')).open('wb')
                    stderr = (directory / (child_kind + '-stderr-private.txt')).open('wb')
                    streams = [stdout, stderr]
                    arguments = ['--prepare-time'] if prepare else ['--once', '--active-only']
                    child = subprocess.Popen([os.sys.executable, str(Path(__file__).resolve()), *arguments],
                                              stdout=stdout, stderr=stderr)
                    state[('time_preparation' if prepare else 'worker') + '_starts'] += 1
                    save()
            except (dbus.DBusException, RuntimeError, subprocess.TimeoutExpired):
                owner, props = None, None
                if state['active']:
                    state['active'] = False
                    save()
            time.sleep(2)
    finally:
        # Do not kill an in-flight QMI transaction; allow its bounded cleanup to finish.
        if child is not None:
            child.wait()
        # Release our own idle lease, while preserving any still-active GPS client.
        if props is not None and power.owned:
            try:
                if not power_snapshot()['enabled'] & 6:
                    power.update(power_snapshot, set_power, dms_operating_mode)
                state['power_policy'] = dict(power.state)
            except (dbus.DBusException, RuntimeError, subprocess.TimeoutExpired):
                pass
        for stream in streams:
            stream.close()
        bus.close()
        state['running'] = False
        save()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--once', action='store_true')
    mode.add_argument('--watch', action='store_true')
    mode.add_argument('--prepare-time', action='store_true')
    parser.add_argument('--active-only', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    if args.watch:
        watch(Path('/var/lib/samurai/gnss-assist'))
        return 0
    result = run_once(Path('/var/lib/samurai/gnss-assist'), args.active_only, args.prepare_time)
    print(json.dumps(result))
    return 0 if result['status'] in ('current', 'refreshed', 'inactive', 'time-prepared') else 1


if __name__ == '__main__':
    raise SystemExit(main())
