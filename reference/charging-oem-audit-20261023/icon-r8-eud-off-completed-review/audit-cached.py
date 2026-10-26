"""Narrow independent arithmetic/hash audit of one completed cached capture.

No candidate/test/main import, device, transport, build or Git invocation.
"""
from pathlib import Path
import base64,hashlib,json,re
HERE=Path(__file__).resolve().parent
REF=HERE.parents[1]/'charging-management-20261023'
BASE=Path('/mnt/e/edk2-samurai-out')
FETCH=BASE/'charging-ui-audit-20261023/icon-capture-r8-eud-off/charging-icon-r8-eud-off-001/fetch-1792777440760431917'
CAP=FETCH/'capture'
POST=BASE/'charging-management-20261023/usb500-default-r1-private'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
load=lambda p:json.loads(p.read_bytes())
report_bytes=(REF/'icon-r8-eud-off-result.json').read_bytes()
report=json.loads(report_bytes);raw=load(CAP/'capture-private.json');receipt=load(FETCH/'fetch-receipt-private.json')
fetched=[]
for name,item in receipt['files'].items():
    retained=(FETCH/name).read_bytes()
    assert retained==base64.b64decode(item['base64'],validate=True)
    assert sha(retained)==item['sha256']
    fetched.append(name)
assert sha((CAP/'capture-private.json').read_bytes())==report['raw_sha256']
assert raw['identity_unchanged'] is receipt['identity_unchanged'] is True
assert receipt['identity_errors']==[]
assert raw['exception'] is None and raw['capture_errors']==raw['event_read_errors']==[]
assert raw['monitor']=={'started':True,'errors':[],'dbus_returncode':-15}
assert receipt['cleanup_state']=={'exact_worker_state':'absent','worker_terminal':True,
    'monitor_started':True,'monitor_errors':[],'dbus_returncode':-15,
    'no_stop_or_cleanup_action_performed':True}
rows=raw['samples'];assert len(rows)==report['sample_count']==267
cycle=raw['cycle'];post=[r for r in rows if r['t_end']>=cycle['online_begin']]
assert len(post)==83 and post[2]['t_end']-post[0]['t_end']>=2
assert all(r['source_online']==r['acok_online']==1 for r in post)
stable=post[2:]
assert len(stable)==81
def source_hardware500(r):
    return (r['source']['current_max_ua']==r['source']['input_current_limit_ua']==500000
        and r['hardware_input']['input_current_limit_ua']==500000
        and r['MaxPower_ma']==500 and r['udc']['state']=='configured')
def report_accepted(r):
    return source_hardware500(r) and r['telemetry']['budget_ua']==500000
assert all(source_hardware500(r) for r in post)
assert not all(report_accepted(r) for r in post)
assert all(report_accepted(r) for r in stable)
assert report['native_source_hardware500_all_reconnect_samples'] is True
assert report['native500_and_charger_telemetry_budget_all_reconnect_samples'] is False
assert report['initial_reconnect_samples']==[{k:r[k] for k in ['t_start','t_end','source','hardware_input','udc','battery','telemetry']} for r in post[:3]]
for r in stable:
    t=r['telemetry']
    assert t['valid']==t['online']==t['protection_ok']==t['desired_enable']==1
    assert 0<=t['age_ms']<=3000
    assert all(t[k]==0 for k in ['shadow','error','stop_error','latched','fault',
        'source_inhibit','thermal_inhibit','cycle_timeout','gauge_charge_stop',
        'logical_full','hold_requested','full_holding','full_cause'])
assert all(0<=r['t_start']<=r['t_end']<=r['t_start']+2 for r in rows)
assert all(a['t_end']<b['t_end'] and 0<=b['t_start']-a['t_end']<=2.5 for a,b in zip(rows,rows[1:]))
duration=(raw['clock_end']['m0']+raw['clock_end']['m1']-raw['clock_start']['m0']-raw['clock_start']['m1'])/2
on_span=post[-1]['t_end']-post[0]['t_end'];stable_span=stable[-1]['t_end']-stable[0]['t_end']
assert abs(duration-raw['duration_seconds'])<1e-9
assert abs(on_span-report['reconnect_observed_seconds'])<1e-9
assert abs(stable_span-report['continuous_after_stable_on_seconds'])<1e-9
assert stable_span>=90 and raw['terminal_reason']=='cycle_complete'
instant=[r['telemetry']['gauge_current_ua'] for r in stable]
assert [min(instant),max(instant)]==report['stable_instant_current_ua_range']==[77000,131000]
assert sum(i>0 for i in instant)==report['stable_positive_instant_samples']==81
assert {r['battery']['status'] for r in stable}=={'Charging'}
# Directly locate actual PropertiesChanged State blocks, without importing the
# production auditor or rerunning its historical test cases.
log=raw['dbus_log'];headers=list(re.finditer(r'^signal time=([0-9.]+).*?path=([^; ]+);[^\n]*member=PropertiesChanged[^\n]*\n',log,re.M))
states=[];device_signals=0
for i,h in enumerate(headers):
    body=log[h.end():headers[i+1].start() if i+1<len(headers) else len(log)]
    interface=re.match(r'\s*string "([^"]+)"',body)
    if interface and interface[1]=='org.freedesktop.UPower.Device':device_signals+=1
    m=re.search(r'string "State"\s+variant\s+uint32 (\d+)',body)
    if m:
        t=(float(h[1])-raw['clock_start']['real'])*duration/(raw['clock_end']['real']-raw['clock_start']['real'])
        states.append(dict(path=h[2],state=int(m[1]),t=t))
assert device_signals==report['dbus_signal_count']==60
assert len(raw['kernel_events'])==report['kernel_event_count']==18
edges=[]
for edge,target in [('detach',2),('attach',1)]:
    reported=next(e for e in report['edges'] if e['edge']==edge)
    source=next(e for e in raw['kernel_events'] if e['POWER_SUPPLY_NAME']=='samurai-usb-input'
        and e.get('POWER_SUPPLY_ONLINE')==str(int(edge=='attach'))
        and (edge=='detach' or e['t']>cycle['offline_begin']))
    display=next(e for e in states if e['path'].endswith('/DisplayDevice') and e['state']==target and e['t']>=source['t'])
    interval=display['t']-source['t']
    assert abs(source['t']-reported['source_uevent_t'])<1e-9
    assert abs(interval-reported['source_to_first_following_display_state_event_seconds_estimated'])<1e-9
    edges.append(dict(edge=edge,target_state=target,source_uevent_t=source['t'],display_estimated_t=display['t'],estimated_interval_seconds=interval))
fresh=load(POST/'post-replug-health-stdout-private.json')
assert fresh==report['fresh_postcheck'] and fresh['passed'] is True and fresh['taint']==0 and fresh['R8_camera_notes_unchanged'] is True
assert fresh['snapshot']['source']['current_max']==fresh['snapshot']['source']['input_current_limit']=='500000'
assert fresh['snapshot']['charger']==dict(input_current_limit=500000,constant_charge_current=250000,constant_charge_voltage=8725000)
screen=load(POST/'screenshot-02-post-replug-private/stdout-private.json')
image=(POST/'screenshot-02-post-replug-private/screen.png').read_bytes()
assert sha(image)==report['screenshot']['sha256'] and base64.b64decode(screen['image_b64'],validate=True)==image
screen_current={k:int(v) for k,v in (s.split('=') for s in screen['telemetry'].split())}['gauge_current_ua']
assert screen_current==report['screenshot']['instant_current_ua']==66000
assert screen['battery']==report['screenshot']['Battery']
assert re.search(r'\bstate:\s+charging\b',screen['upower_text'].split('Device: /org/freedesktop/UPower/devices/DisplayDevice',1)[1].split('Daemon:',1)[0])
assert (REF/'icon-r8-eud-off-result.json').read_bytes()==report_bytes
result=dict(schema='charging-icon-r8-eud-off-completed-independent-review-v1',
    conclusion='no_blocking_issue_in_report_scope',report_sha256=sha(report_bytes),
    report_generator_sha256=sha((REF/'report-r8-eud-off-icon.py').read_bytes()),
    raw_sha256=sha((CAP/'capture-private.json').read_bytes()),fetch_receipt_sha256=sha((FETCH/'fetch-receipt-private.json').read_bytes()),
    fetched_files_checked=len(fetched),sample_count=len(rows),duration_seconds=duration,
    DBus_Device_PropertiesChanged_count=device_signals,DBus_all_PropertiesChanged_count=len(headers),
    on_samples=len(post),on_observed_seconds=on_span,stable_samples=len(stable),stable_observed_seconds=stable_span,
    native_source_hardware500_all_on_samples=True,report_combined_predicate_all_on_samples=False,
    report_combined_predicate_all_stable_samples=True,stable_instant_current_ua_range=[min(instant),max(instant)],
    stable_positive_instant_samples=sum(i>0 for i in instant),edges=edges,
    first_reconnect=dict(t=post[0]['t_end'],source_native_hardware500=True,telemetry_valid=post[0]['telemetry']['valid'],
        telemetry_budget_ua=post[0]['telemetry']['budget_ua'],telemetry_error=post[0]['telemetry']['error'],Battery=post[0]['battery']['status']),
    second_reconnect=dict(t=post[1]['t_end'],instant_current_ua=post[1]['telemetry']['gauge_current_ua'],Battery=post[1]['battery']['status']),
    screenshot_sha256=sha(image),screenshot_charging_lightning_visually_present=True,
    scope_notes=[
        'The false all-reconnect compound result also requires fresh charger telemetry budget500, not only native/source/hardware500. It must not be read as evidence of late host authorization.',
        'Source online attach uevent precedes confirmed effective500; event timing uses this source-online reference, not a budget500 event.',
        'Stable charging is supported at observed samples; sequential sysfs reads and sampled telemetry do not prove an atomic or uninterrupted analogue current trace.',
        'Endpoint-mapped State2/State1 intervals are notification observations, not plug-edge or screen-frame latency.',
        'Later screenshot and qualitative human feedback support visible improvement, not a measured pixel latency SLA.',
        'No cold-boot, PM, complete charging-mode or causal isolation acceptance is inferred.'
    ],tests_rerun=False,collector_executed=False,device_accessed=False,build_invoked=False,Git_invoked=False)
(HERE/'review.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ['conclusion','fetched_files_checked','sample_count','stable_samples','stable_observed_seconds','report_sha256']}))
