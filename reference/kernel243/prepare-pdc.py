"""Adapt the proven read-only PDC exchange, preserving ACK/indication cleanup."""
from pathlib import Path
R=Path(__file__).resolve().parent
s=(R.parent/'kernel206/query-pdc-details.py').read_text()
s=s.replace("out = root / 'k206-pdc-details'","out = root / 'k243-pdc-readonly'")
s=s.replace("root / 'k205r2-runtime/boot-id-private.txt'","root / 'k236-runtime/boot-id-private.txt'")
s=s.replace("props = dbus.Interface(bus.get_object('org.freedesktop.ModemManager1', '/org/freedesktop/ModemManager1/Modem/0'), 'org.freedesktop.DBus.Properties')", "objects=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects()\npaths=[str(p) for p,v in objects.items() if 'org.freedesktop.ModemManager1.Modem' in v];assert len(paths)==1\nprops=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1',paths[0]),'org.freedesktop.DBus.Properties')")
s=s.replace("if operation == 'list':\n                getters", "if operation == 'selected':\n                getters=[(name,lambda name=name:bytes(getattr(output,'get_'+name)()).hex()) for name in ['active_id','pending_id']]\n            elif operation == 'list':\n                getters")
s=s.replace("output = getattr(source, 'list_configs_finish' if operation == 'list' else 'get_config_info_finish')(result)", "output=getattr(source,{'selected':'get_selected_config_finish','list':'list_configs_finish','info':'get_config_info_finish'}[operation])(result)")
s=s.replace("signal_name = 'list-configs' if operation == 'list' else 'get-config-info'", "signal_name={'selected':'get-selected-config','list':'list-configs','info':'get-config-info'}[operation]")
s=s.replace("if operation == 'list':\n            request = Qmi.MessagePdcListConfigsInput.new()", "if operation=='selected':\n            request=Qmi.MessagePdcGetSelectedConfigInput.new()\n            request.set_config_type(getattr(Qmi.PdcConfigurationType,kind.upper()))\n        elif operation == 'list':\n            request = Qmi.MessagePdcListConfigsInput.new()")
s=s.replace("getattr(client, 'list_configs' if operation == 'list' else 'get_config_info')(request, 10, cancel, acknowledged, None)", "getattr(client,{'selected':'get_selected_config','list':'list_configs','info':'get_config_info'}[operation])(request,10,cancel,acknowledged,None)")
start=s.index('try:\n    results = {}\n    matches = {}')
s=s[:start]+'''try:
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
    (out/'summary.json').write_text(json.dumps(report,indent=2)+'\\n')
    print(json.dumps(report),flush=True)
finally:
    bus.close()
'''
assert s.count("'selected'")>=5 and 'stage=206' not in s
compile(s,'query-pdc.py','exec');(R/'query-pdc.py').write_text(s)
print('Prepared read-only selected/list/info PDC collector')
