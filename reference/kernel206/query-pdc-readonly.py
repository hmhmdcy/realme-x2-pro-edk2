"""Get selected PDC platform/software configurations, with independent cleanup."""
from pathlib import Path
import dbus, gi, json, os, subprocess, time, traceback
gi.require_version('Qmi', '1.0')
gi.require_version('Qrtr', '1.0')
from gi.repository import Qmi, Qrtr, GLib, Gio

os.umask(0o077)
root = Path('/var/lib/samurai')
out = root / 'k206-pdc-queries-r2'
assert not out.exists()
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == (root / 'k205r2-runtime/boot-id-private.txt').read_bytes()
bus = dbus.SystemBus(private=True)
props = dbus.Interface(bus.get_object('org.freedesktop.ModemManager1', '/org/freedesktop/ModemManager1/Modem/0'), 'org.freedesktop.DBus.Properties')
assert int(props.Get('org.freedesktop.ModemManager1.Modem.Location', 'Enabled')) == 0
owner = str(bus.get_name_owner('org.freedesktop.ModemManager1'))
out.mkdir(mode=0o700)
(out / 'boot-id-private.txt').write_bytes(boot)

def exchange(kind, token):
    state = dict(kind=kind, ack=False, indication=False, errors=[], order=[])
    objects = dict(device=None, client=None, bus=None, pending=True, closing=False, cleanup=False, signal=None)
    cancel, loop, timers = Gio.Cancellable(), GLib.MainLoop(), []
    def end():
        loop.quit()
        return False
    def closed(source, result, *_):
        try:
            state['device_closed'] = bool(source.close_finish(result))
        except Exception as error:
            state['errors'].append(type(error).__name__ + ': ' + str(error))
        end()
    def released(source, result, *_):
        try:
            state['client_released'] = bool(source.release_client_finish(result))
        except Exception as error:
            state['errors'].append(type(error).__name__ + ': ' + str(error))
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
            device.release_client(client, Qmi.DeviceReleaseClientFlags.RELEASE_CID, 10, None, released, None)
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
                state['errors'].append(type(error).__name__ + ': ' + str(error))
                cleanup()
        return wrapped
    def complete():
        if state['ack'] and state['indication']:
            cleanup()
    def indication(_client, output):
        try:
            if output.get_token() != token:
                state['ignored_other_tokens'] = state.get('ignored_other_tokens', 0) + 1
                return
            state['status'] = int(output.get_indication_result())
            for name in ['active_id', 'pending_id']:
                try:
                    state[name] = bytes(getattr(output, 'get_' + name)()).hex()
                except GLib.Error as error:
                    if error.matches(Qmi.core_error_quark(), Qmi.CoreError.TLVNOTFOUND):
                        state[name] = None
                    else:
                        raise
            state['indication'] = True
            state['order'].append('indication')
            complete()
        except Exception as error:
            state['errors'].append(type(error).__name__ + ': ' + str(error))
            cleanup()
    @callback
    def acknowledged(source, result, *_):
        output = source.get_selected_config_finish(result)
        output.get_result()
        state['ack'] = True
        state['order'].append('ack')
        if objects['closing']:
            cleanup()
        else:
            complete()
    @callback
    def allocated(source, result, *_):
        client = objects['client'] = source.allocate_client_finish(result)
        if objects['closing']:
            cleanup()
            return
        objects['signal'] = client.connect('get-selected-config', indication)
        request = Qmi.MessagePdcGetSelectedConfigInput.new()
        request.set_config_type(getattr(Qmi.PdcConfigurationType, kind.upper()))
        request.set_token(token)
        objects['pending'] = True
        client.get_selected_config(request, 10, cancel, acknowledged, None)
    @callback
    def opened(source, result, *_):
        assert source.open_finish(result)
        if objects['closing']:
            cleanup()
            return
        objects['pending'] = True
        source.allocate_client(Qmi.Service.PDC, Qmi.CID_NONE, 10, cancel, allocated, None)
    @callback
    def ready(source, result, *_):
        device = objects['device'] = Qmi.Device.new_from_node_finish(result)
        if objects['closing']:
            cleanup()
            return
        objects['pending'] = True
        device.open(Qmi.DeviceOpenFlags.EXPECT_INDICATIONS, 10, cancel, opened, None)
    @callback
    def bus_ready(source, result, *_):
        objects['bus'] = Qrtr.Bus.new_finish(result)
        if objects['closing']:
            cleanup()
            return
        node = objects['bus'].get_node(0)
        assert node is not None
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
    timers.extend([GLib.timeout_add_seconds(35, expired), GLib.timeout_add_seconds(65, cleanup_expired)])
    Qrtr.Bus.new(2000, cancel, bus_ready, None)
    loop.run()
    for timer in timers:
        if GLib.MainContext.default().find_source_by_id(timer) is not None:
            GLib.source_remove(timer)
    (out / (kind + '-selected-private.json')).write_text(json.dumps(state, indent=2) + '\n')
    return state

try:
    results = {kind: exchange(kind, 2060 + index) for index, kind in enumerate(['platform', 'software'])}
    assert all(s['ack'] and s['indication'] and s.get('client_released') and s.get('device_closed') and not s['errors'] for s in results.values())
    lists = {}
    for kind in ['platform', 'software']:
        p = subprocess.run(['qmicli', '-d', 'qrtr://0', '--device-open-proxy', '--pdc-list-configs=' + kind], capture_output=True, timeout=35)
        (out / (kind + '-list-private.log')).write_bytes(p.stdout + p.stderr)
        lists[kind] = dict(exit=p.returncode, bytes=len(p.stdout) + len(p.stderr))
    assert str(bus.get_name_owner('org.freedesktop.ModemManager1')) == owner
    assert int(props.Get('org.freedesktop.ModemManager1.Modem.Location', 'Enabled')) == 0
    assert boot == Path('/proc/sys/kernel/random/boot_id').read_bytes()
    summary = {kind: {key: state.get(key) for key in ['ack', 'indication', 'status', 'client_released', 'device_closed', 'order']} | dict(active_id_present=bool(state.get('active_id')), pending_id_present=bool(state.get('pending_id')), errors=len(state['errors'])) for kind, state in results.items()}
    result = dict(stage=206, current_r2_boot_verified=True, selected_config_queries=summary, list_config_queries=lists, read_only=True, no_config_load_select_activate=True, gps_enabled=0, modem_owner_unchanged=True, modem_restarted=False, taint=int(Path('/proc/sys/kernel/tainted').read_text()), uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]))
    (out / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
finally:
    bus.close()
