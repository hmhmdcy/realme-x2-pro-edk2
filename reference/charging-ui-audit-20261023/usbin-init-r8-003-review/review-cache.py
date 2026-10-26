"""USBIN003 retained-cache review only. No transport or device actions."""
from pathlib import Path
from collections import Counter
import hashlib
import importlib.util
import json
import re

HERE=Path(__file__).resolve().parent
BASE=Path('/mnt/e/edk2-samurai-out/charging-oem-audit-20261023/usbin-init-host/usbin-init-r8-003/fetch-1792764030744355505')
CAP=BASE/'capture'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
raw=json.loads((CAP/'capture-private.json').read_bytes())
result=json.loads((CAP/'result.json').read_bytes())
fetch=json.loads((BASE/'fetch-receipt-private.json').read_bytes())
assert raw['terminal_reason']=='cycle_complete' and len(raw['samples'])==362
assert all(result[k] is True for k in ['initialization_verified','physical_cycle_passed','environment_unchanged','post_online_telemetry_healthy','cv_cap_preserved'])
assert raw['identity_unchanged'] and not raw['capture_errors'] and not raw['event_read_errors'] and not raw['exception']
assert fetch['identity_unchanged'] and not fetch['fetch_errors'] and all(s['state']=='absent' for s in fetch['processes'].values())
assert sha((BASE/'icon-audit.py').read_bytes())=='7a7c5342fcdef85b5d941d7d9cb351a240d561b9d219817790f63c4825a7a287'
spec=importlib.util.spec_from_file_location('frozen003audit',BASE/'icon-audit.py')
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
# Extend only parsing to retain the daemon's OnBattery property; no raw lines exported.
heads=list(audit.SIGNAL.finditer(raw['dbus_log']));signals=[]
for i,head in enumerate(heads):
    body=raw['dbus_log'][head.end():heads[i+1].start() if i+1<len(heads) else len(raw['dbus_log'])]
    m=re.match(r'\s*string ("(?:[^"\\]|\\.)*")',body)
    assert m and body.rstrip().endswith(']')
    vals={}
    for prop in audit.PROPERTY.finditer(body):
        key=json.loads(prop[1]);kind=prop[2];value=prop[3].strip()
        if key not in ['State','Online','OnBattery']:continue
        if kind=='boolean':assert value in ['true','false'];value=value=='true'
        else:assert key=='State' and kind=='uint32';value=int(value);assert 0<=value<=6
        vals[key]=value
    if vals:signals.append({'realtime':float(head[1]),'path':head[2],'interface':json.loads(m[1]),'values':vals})
mapped,clocks=audit.mapped_signals(signals,raw['clock_start'],raw['clock_end'])
assert clocks['endpoints_consistent']
def label(path):
    if path==audit.DISPLAY:return 'Display'
    if '/battery_' in path:return 'Battery'
    if path.endswith('/line_power_samurai_usb_input'):return 'Source line power'
    if path.endswith('/line_power_mp2650_input'):return 'Charger line power'
    if path=='/org/freedesktop/UPower':return 'UPower daemon'
    raise ValueError('unclassified selected D-Bus object')
dbus=[{'t_seconds':s['estimated_t'],'object':label(s['path']),**s['values']} for s in mapped]
def kev(name,**values):
    return next(e for e in raw['kernel_events'] if e.get('POWER_SUPPLY_NAME')==name and all(e.get(k)==v for k,v in values.items()))
off=kev('mp2650-input',POWER_SUPPLY_ONLINE='0')['t']
on=next(e['t'] for e in raw['kernel_events'] if e['t']>off and e.get('POWER_SUPPLY_NAME')=='mp2650-input' and e.get('POWER_SUPPLY_ONLINE')=='1')
def db(object,key,value,start=0,end=float('inf')):
    return next((s['t_seconds'] for s in dbus if s['object']==object and s.get(key)==value and start<=s['t_seconds']<end),None)
def ktime(name,key,value,start=0,end=float('inf')):
    return next((s['t'] for s in raw['kernel_events'] if s.get('POWER_SUPPLY_NAME')==name and s.get(key)==value and start<=s['t']<end),None)
battery=raw['battery_name']
timeline={
    'baseline_battery_uevent_Charging':ktime(battery,'POWER_SUPPLY_STATUS','Charging'),
    'baseline_UPower_Battery_State1':db('Battery','State',1),
    'baseline_UPower_Display_State1':db('Display','State',1),
    'detach_source_name_only_uevent':next(e['t'] for e in raw['kernel_events'] if e.get('POWER_SUPPLY_NAME')=='samurai-usb-input' and 'POWER_SUPPLY_ONLINE' not in e),
    'detach_ACOK_uevent_online0':off,
    'detach_source_uevent_online0':ktime('samurai-usb-input','POWER_SUPPLY_ONLINE','0'),
    'detach_UPower_source_Online_false':db('Source line power','Online',False,off-1,on),
    'detach_UPower_charger_Online_false':db('Charger line power','Online',False,off-1,on),
    'detach_Battery_uevent_Discharging':ktime(battery,'POWER_SUPPLY_STATUS','Discharging',off,on),
    'detach_UPower_Battery_State2':db('Battery','State',2,off,on),
    'detach_UPower_Display_State2':db('Display','State',2,off,on),
    'detach_UPower_OnBattery_true':db('UPower daemon','OnBattery',True,off,on),
    'attach_ACOK_uevent_online1':on,
    'attach_source_uevent_online1':ktime('samurai-usb-input','POWER_SUPPLY_ONLINE','1',on),
    'attach_source_uevent_budget100000':ktime('samurai-usb-input','POWER_SUPPLY_CURRENT_MAX','100000',on),
    'attach_UPower_charger_Online_true':db('Charger line power','Online',True,on),
    'attach_UPower_source_Online_true':db('Source line power','Online',True,on),
    'attach_UPower_OnBattery_false':db('UPower daemon','OnBattery',False,on),
    'attach_converter_uevent_Charging':ktime('mp2650-input','POWER_SUPPLY_STATUS','Charging',on),
    'attach_Battery_uevent_Charging':ktime(battery,'POWER_SUPPLY_STATUS','Charging',on),
    'attach_UPower_Battery_State1':db('Battery','State',1,on),
    'attach_UPower_Display_State1':db('Display','State',1,on)}
delta=lambda a,b:None if a is None or b is None else a-b
latencies={
    'baseline_battery_uevent_to_correct_State1':delta(timeline['baseline_UPower_Battery_State1'],timeline['baseline_battery_uevent_Charging']),
    'detach_ACOK0_to_Battery_State2':delta(timeline['detach_UPower_Battery_State2'],off),
    'detach_ACOK0_to_Display_State2':delta(timeline['detach_UPower_Display_State2'],off),
    'detach_source0_to_Battery_State2':delta(timeline['detach_UPower_Battery_State2'],timeline['detach_source_uevent_online0']),
    'detach_ACOK0_to_Battery_Discharging_uevent':delta(timeline['detach_Battery_uevent_Discharging'],off),
    'detach_Battery_uevent_to_State2_signed_not_causal':delta(timeline['detach_UPower_Battery_State2'],timeline['detach_Battery_uevent_Discharging']),
    'attach_ACOK1_to_charger_Online_true':delta(timeline['attach_UPower_charger_Online_true'],on),
    'attach_source1_to_source_Online_true':delta(timeline['attach_UPower_source_Online_true'],timeline['attach_source_uevent_online1']),
    'attach_ACOK1_to_OnBattery_false':delta(timeline['attach_UPower_OnBattery_false'],on),
    'attach_ACOK1_to_converter_Charging':delta(timeline['attach_converter_uevent_Charging'],on)}
rows=raw['samples'];post=[r for r in rows if r['t_end']>=on]
known=lambda xs:sorted({x for x in xs if type(x) is int})
def summary(rs):
    return {'samples':len(rs),'Battery_status_counts':dict(Counter(r['battery']['status'] for r in rs)),
        'Battery_current_now_ua_range':[min(r['battery']['current_now_ua'] for r in rs),max(r['battery']['current_now_ua'] for r in rs)],
        'known_source_budget_ua':known(r['source']['usb']['current_max'] for r in rs),
        'known_native_limit_ua':known(r['source']['usb']['input_current_limit'] for r in rs),
        'input_limit_ua':known(r['source']['charger']['input_current_limit'] for r in rs),
        'CC_request_ua':known(r['source']['charger']['constant_charge_current'] for r in rs),
        'pack_CV_uv':known(r['source']['charger']['constant_charge_voltage'] for r in rs),
        'USB_type_strings':sorted({r['source']['usb']['usb_type'] for r in rs}),
        'budget_ENODATA_samples':sum(isinstance(r['source']['usb']['current_max'],dict) for r in rs),
        'native_ENODATA_samples':sum(isinstance(r['source']['usb']['input_current_limit'],dict) for r in rs)}
post_summary=summary(post)
assert post_summary['Battery_status_counts']=={'Discharging':51} and post_summary['Battery_current_now_ua_range']==[-45000,-20000]
assert known(r['source']['usb']['current_max'] for r in rows)==[0,100000]
assert known(r['source']['usb']['input_current_limit'] for r in rows)==[100000]
for e in raw['kernel_events']:
    if e.get('POWER_SUPPLY_NAME')=='samurai-usb-input':
        for key in ['POWER_SUPPLY_CURRENT_MAX','POWER_SUPPLY_INPUT_CURRENT_LIMIT']:
            if key in e:assert int(e[key]) in [0,100000]
assert not any(s.get('State')==1 and s['t_seconds']>=on for s in dbus)
kernel_selected=[]
for e in raw['kernel_events']:
    obj={'mp2650-input':'Charger','samurai-usb-input':'Source',battery:'Battery'}.get(e.get('POWER_SUPPLY_NAME'))
    if not obj:continue
    selected={k.removeprefix('POWER_SUPPLY_'):e[k] for k in ['POWER_SUPPLY_ONLINE','POWER_SUPPLY_STATUS','POWER_SUPPLY_CURRENT_NOW','POWER_SUPPLY_CURRENT_MAX','POWER_SUPPLY_INPUT_CURRENT_LIMIT','POWER_SUPPLY_USB_TYPE'] if k in e}
    kernel_selected.append({'t_seconds':e['t'],'object':obj,'properties':selected})
first_charging=next(i for i,r in enumerate(rows) if r['battery']['status']=='Charging')
off_discharge=next(i for i,r in enumerate(rows) if r['t_end']>=off and r['battery']['status']=='Discharging')
interval=lambda i:[rows[i-1]['t_end'],rows[i]['t_end']]
report={'scope':'USBIN003 retained capture, offline independent value-directed review',
    'passed_cache_checks':True,'raw_input_sha256':{name:sha((CAP/name).read_bytes()) for name in ['capture-private.json','result.json','kernel-events-private.jsonl','upower-dbus-private.log','samples-private.jsonl','clock-start.json','clock-end.json']},
    'fetch_receipt_sha256':sha((BASE/'fetch-receipt-private.json').read_bytes()),
    'duration_seconds':raw['duration_seconds'],'samples':len(rows),'terminal_reason':raw['terminal_reason'],
    'physical_cycle_passed':True,'environment_health_CV_capture_gates_passed':True,'owned_processes_at_fetch':{'absent':len(fetch['processes'])},
    'clock_mapping':clocks,'times_are':'seconds from capture start; netlink receipt and endpoint-mapped D-Bus times, not cable/pixel times',
    'timeline':timeline,'intervals_seconds':latencies,'selected_kernel_events':kernel_selected,'selected_dbus_changes':dbus,
    'standard_Battery_Charging_first_sample_interval_seconds':interval(first_charging),
    'standard_Battery_Discharging_after_detach_first_sample_interval_seconds':interval(off_discharge),
    'all_samples_summary':summary(rows),'post_attach_summary':post_summary,
    'post_attach_last_sample_after_ACOK1_seconds':rows[-1]['t_end']-on,
    'helper':{k:result['helper_terminal'][k] for k in ['phase','before_cfg','after_cfg','write_attempted','write_return','readback_error','post_error','unknown_write']},
    'conclusions':{
        'source_budget_ever_above_100mA_in_known_samples_or_events':False,
        'post_attach_Charging_State_delayed_proven':False,
        'post_attach_no_Charging_State_has_matching_net_Discharging_samples':True,
        'detach_correct_State2_delayed_about_4s_from_digital_supply_off':True,
        'Battery_uevent_then_State2_serial_causal_chain_supported':False,
        'screen_pixel_delay_measured':False,
        'bit_clear_caused_budget_upgrade_proven':False},
    'user_observation_only':{'unplug_icon_estimate_seconds':6,'replug_no_charging_icon_estimate_seconds_greater_than':60,'clock_aligned_to_capture':False},
    'limitations':['No screen recording/pixel timestamp. User estimates are separate from telemetry.',
        'D-Bus State1 means Charging; State2 means Discharging. First opposite State is never used as the intended response.',
        'Online1/OnBattery=false proves external power presence, not positive net Battery current.',
        'Offline telemetry flags are cleared by the collector/driver and flags_fresh=false; zero is not a raw gauge-flags reading.',
        'A transient ENODATA source/native read is not authorization and is not silently replaced by100mA.',
        'No inference beyond this capture; finish/commit/unload was root-owned and not performed by this review.'],
    'device_accessed':False,'SSH_executed':False,'controller_helper_modified':False,'raw_logs_or_private_identity_exported':False}
text=json.dumps(report,indent=2)+'\n'
assert not re.search(r'[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}',text)
assert not re.search(r'(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}',text)
(HERE/'review.json').write_text(text)
print(json.dumps({'passed':True,'timeline':timeline,'intervals_seconds':latencies,'post_attach_summary':post_summary,'review_sha256':sha(text.encode())},indent=2))
