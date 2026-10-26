from pathlib import Path
here = Path(__file__).resolve().parent
source = (here / 'query-pdc-readonly.py').read_text()
source = source.replace("out = root / 'k206-pdc-queries-r2'", "out = root / 'k206-pdc-details'")
source = source.replace('def exchange(kind, token):', "def exchange(kind, token, operation, config_id=None):")
source = source.replace("state = dict(kind=kind, ack=False", "state = dict(kind=kind, operation=operation, ack=False")
start = source.index("            for name in ['active_id', 'pending_id']:")
end = source.index("            state['indication'] = True", start)
source = source[:start] + '''            if operation == 'list':
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
''' + source[end:]
source = source.replace('output = source.get_selected_config_finish(result)', "output = getattr(source, 'list_configs_finish' if operation == 'list' else 'get_config_info_finish')(result)")
start = source.index("        objects['signal'] = client.connect('get-selected-config', indication)")
end = source.index('    @callback\n    def opened', start)
source = source[:start] + '''        signal_name = 'list-configs' if operation == 'list' else 'get-config-info'
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
''' + source[end:]
source = source.replace("(kind + '-selected-private.json')", "(kind + '-' + operation + '-private.json')")
start = source.index('\ntry:\n    results = ')
source = source[:start] + '''
try:
    results = {}
    matches = {}
    for index, kind in enumerate(['platform', 'software']):
        selected = json.loads((root / 'k206-pdc-queries-r2' / (kind + '-selected-private.json')).read_text())
        assert selected['status'] == 0 and selected['active_id']
        listed = results[kind + '_list'] = exchange(kind, 20620 + index, 'list')
        info = results[kind + '_info'] = exchange(kind, 20630 + index, 'info', selected['active_id'])
        matches[kind] = any(c['id'] == selected['active_id'] for c in (listed.get('configs') or []))
    assert str(bus.get_name_owner('org.freedesktop.ModemManager1')) == owner
    assert int(props.Get('org.freedesktop.ModemManager1.Modem.Location', 'Enabled')) == 0
    assert boot == Path('/proc/sys/kernel/random/boot_id').read_bytes()
    summary = {label: {key: state.get(key) for key in ['ack', 'indication', 'status', 'client_released', 'device_closed', 'order']} | dict(errors=len(state['errors']), configs_count=len(state.get('configs') or []), description_present=bool(state.get('description'))) for label, state in results.items()}
    result = dict(stage=206, current_r2_boot_verified=True, queries=summary, active_id_found_in_list=matches, read_only=True, no_config_load_select_activate=True, gps_enabled=0, modem_owner_unchanged=True, modem_restarted=False, taint=int(Path('/proc/sys/kernel/tainted').read_text()), uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]))
    (out / 'summary.json').write_text(json.dumps(result, indent=2) + '\\n')
    print(json.dumps(result))
finally:
    bus.close()
'''
compile(source, 'query-pdc-details.py', 'exec')
assert 'set_selected_config' not in source and 'activate_config' not in source and 'load_config' not in source
(here / 'query-pdc-details.py').write_text(source)
print('Prepared read-only PDC list and selected-config metadata queries.')
