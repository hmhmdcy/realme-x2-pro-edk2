"""Get selected PDC platform/software configurations, with independent cleanup."""
from pathlib import Path
import dbus, gi, json, os, subprocess, time, traceback
gi.require_version('Qmi', '1.0')
gi.require_version('Qrtr', '1.0')
from gi.repository import Qmi, Qrtr, GLib, Gio

os.umask(0o077)
root = Path('/var/lib/samurai')
out = root / 'k243-pdc-readonly'
assert not out.exists()
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == (root / 'k236-runtime/boot-id-private.txt').read_bytes()
bus = dbus.SystemBus(private=True)
objects=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
paths=[str(p) for p,v in objects.items() if 'org.freedesktop.ModemManager1.Modem' in v];assert len(paths)==1
props=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1',paths[0]),'org.freedesktop.DBus.Properties')
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
            if operation == 'selected':
                getters=[(name,lambda name=name:bytes(getattr(output,'get_'+name)()).hex()) for name in ['active_id','pending_id']]
            elif operation == 'list':
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
        output=getattr(source,{'selected':'get_selected_config_finish','list':'list_configs_finish','info':'get_config_info_finish'}[operation])(result)
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
        signal_name={'selected':'get-selected-config','list':'list-configs','info':'get-config-info'}[operation]
        objects['signal'] = client.connect(signal_name, indication)
        if operation=='selected':
            request=Qmi.MessagePdcGetSelectedConfigInput.new()
            request.set_config_type(getattr(Qmi.PdcConfigurationType,kind.upper()))
        elif operation == 'list':
            request = Qmi.MessagePdcListConfigsInput.new()
            request.set_config_type(getattr(Qmi.PdcConfigurationType, kind.upper()))
        else:
            request = Qmi.MessagePdcGetConfigInfoInput.new()
            request.set_type_with_id_v2(getattr(Qmi.PdcConfigurationType, kind.upper()), list(bytes.fromhex(config_id)))
        request.set_token(token)
        objects['pending'] = True
        getattr(client,{'selected':'get_selected_config','list':'list_configs','info':'get_config_info'}[operation])(request,10,cancel,acknowledged,None)
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
    results={};matches={};unchanged={}
    for index,kind in enumerate(['platform','software']):
        selected=results[kind+'_selected']=exchange(kind,24300+index,'selected')
        assert selected.get('status')==0 and selected.get('active_id') and not selected['errors']
        assert selected.get('client_released') and selected.get('device_closed')
        old=json.loads((root/'k207-pdc-queries'/ (kind+'-selected-private.json')).read_text()) if (root/'k207-pdc-queries'/ (kind+'-selected-private.json')).exists() else None
        unchanged[kind]=selected['active_id']==old.get('active_id') if old else None
        listed=results[kind+'_list']=exchange(kind,24310+index,'list')
        info=results[kind+'_info']=exchange(kind,24320+index,'info',selected['active_id'])
        matches[kind]=any(x['id']==selected['active_id'] for x in (listed.get('configs') or []))
        assert all(x.get('status')==0 and x.get('ack') and x.get('indication') and x.get('client_released') and x.get('device_closed') and not x['errors'] for x in [listed,info])
    assert str(bus.get_name_owner('org.freedesktop.ModemManager1'))==owner
    assert int(props.Get('org.freedesktop.ModemManager1.Modem.Location','Enabled'))==0
    assert boot==Path('/proc/sys/kernel/random/boot_id').read_bytes()
    summary={label:{k:value.get(k) for k in ['ack','indication','status','client_released','device_closed','order']}|dict(errors=len(value['errors']),configs_count=len(value.get('configs') or []),active_id_present=bool(value.get('active_id')),pending_id_present=bool(value.get('pending_id')),description_present=bool(value.get('description'))) for label,value in results.items()}
    report=dict(stage=243,current236_boot=True,queries=summary,active_id_in_list=matches,active_id_matches207=unchanged,read_only=True,no_config_load_select_activate=True,no_gnss_started=True,modem_owner_preserved=True,taint=int(Path('/proc/sys/kernel/tainted').read_text()))
    (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)
finally:
    bus.close()
