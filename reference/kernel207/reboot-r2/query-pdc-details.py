"""Get selected PDC platform/software configurations, with independent cleanup."""
from pathlib import Path
import dbus, gi, json, os, subprocess, time, traceback
gi.require_version('Qmi', '1.0')
gi.require_version('Qrtr', '1.0')
from gi.repository import Qmi, Qrtr, GLib, Gio

os.umask(0o077)
root = Path('/var/lib/samurai')
out = root / 'k207r2-pdc-details'
assert not out.exists()
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == (root / 'k207r2-runtime/boot-id-private.txt').read_bytes()
bus = dbus.SystemBus(private=True)
props = dbus.Interface(bus.get_object('org.freedesktop.ModemManager1', '/org/freedesktop/ModemManager1/Modem/0'), 'org.freedesktop.DBus.Properties')
assert int(props.Get('org.freedesktop.ModemManager1.Modem.Location', 'Enabled')) == 0
owner = str(bus.get_name_owner('org.freedesktop.ModemManager1'))
out.mkdir(mode=0o700)
(out / 'boot-id-private.txt').write_bytes(boot)

def exchange(kind, token, operation, config_id=None):
    state = dict(kind=kind, operation=operation, ack=False, indication=False, errors=[], order=[])
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
            if operation == 'list':
                getters = [('configs', lambda: [dict(type=int(c.config_type), id=bytes(c.id).hex()) for c in output.get_configs()])]
            else:
                getters = [(name, getattr(output, 'get_' + name)) for name in ['description', 'total_size', 'version']]
            for name, getter in getters:
                try:
                    state[name] = getter()
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
        output = getattr(source, 'list_configs_finish' if operation == 'list' else 'get_config_info_finish')(result)
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
        signal_name = 'list-configs' if operation == 'list' else 'get-config-info'
        objects['signal'] = client.connect(signal_name, indication)
        if operation == 'list':
            request = Qmi.MessagePdcListConfigsInput.new()
            request.set_config_type(getattr(Qmi.PdcConfigurationType, kind.upper()))
        else:
            request = Qmi.MessagePdcGetConfigInfoInput.new()
            request.set_type_with_id_v2(getattr(Qmi.PdcConfigurationType, kind.upper()), list(bytes.fromhex(config_id)))
        request.set_token(token)
        objects['pending'] = True
        getattr(client, 'list_configs' if operation == 'list' else 'get_config_info')(request, 10, cancel, acknowledged, None)
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
    (out / (kind + '-' + operation + '-private.json')).write_text(json.dumps(state, indent=2) + '\n')
    return state

try:
    results = {}
    matches = {}
    for index, kind in enumerate(['platform', 'software']):
        selected = json.loads((root / 'k207r2-pdc-queries-r2' / (kind + '-selected-private.json')).read_text())
        assert selected['status'] == 0 and selected['active_id']
        listed = results[kind + '_list'] = exchange(kind, 20620 + index, 'list')
        info = results[kind + '_info'] = exchange(kind, 20630 + index, 'info', selected['active_id'])
        matches[kind] = any(c['id'] == selected['active_id'] for c in (listed.get('configs') or []))
    assert str(bus.get_name_owner('org.freedesktop.ModemManager1')) == owner
    assert int(props.Get('org.freedesktop.ModemManager1.Modem.Location', 'Enabled')) == 0
    assert boot == Path('/proc/sys/kernel/random/boot_id').read_bytes()
    summary = {label: {key: state.get(key) for key in ['ack', 'indication', 'status', 'client_released', 'device_closed', 'order']} | dict(errors=len(state['errors']), configs_count=len(state.get('configs') or []), description_present=bool(state.get('description'))) for label, state in results.items()}
    result = dict(stage=207, current_second207_boot_verified=True, queries=summary, active_id_found_in_list=matches, read_only=True, no_config_load_select_activate=True, gps_enabled=0, modem_owner_unchanged=True, modem_restarted=False, taint=int(Path('/proc/sys/kernel/tainted').read_text()), uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]))
    (out / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
finally:
    bus.close()
