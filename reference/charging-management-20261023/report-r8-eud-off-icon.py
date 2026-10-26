"""Audit the completed real cycle and its native500 recovery; no device access."""
from pathlib import Path
import hashlib,importlib.util,json,re,sys

REF=Path(__file__).resolve().parent
BASE=Path('/mnt/e/edk2-samurai-out')
RUN=BASE/'charging-ui-audit-20261023/icon-capture-r8-eud-off/charging-icon-r8-eud-off-001'
FETCH=RUN/'fetch-1792777440760431917'
CAPTURE=FETCH/'capture'
LEAF=REF.parent/'charging-oem-audit-20261023/icon-capture-r8-eud-off-candidate'
sha=lambda b:hashlib.sha256(b).hexdigest()

def main():
 raw=json.loads((CAPTURE/'capture-private.json').read_bytes())
 result=json.loads((CAPTURE/'result.json').read_bytes())
 receipt=json.loads((FETCH/'fetch-receipt-private.json').read_bytes())
 assert receipt['identity_unchanged'] and receipt['cleanup_state']=={
  'exact_worker_state':'absent','worker_terminal':True,'monitor_started':True,
  'monitor_errors':[],'dbus_returncode':-15,'no_stop_or_cleanup_action_performed':True}
 assert result['physical_cycle_passed'] and result['terminal_reason']=='cycle_complete'
 assert not result['dbus_parse_errors'] and result['clock_mapping']['endpoints_consistent']
 assert sha((LEAF/'capture-entry.py').read_bytes())=='70fdc224f337e8f2e712aa3d8a8d2bf2bda1de0c224c17dc261287b9fa63b44d'
 sys.path.insert(0,str(LEAF))
 spec=importlib.util.spec_from_file_location('retained_entry',LEAF/'capture-entry.py')
 entry=importlib.util.module_from_spec(spec);spec.loader.exec_module(entry)
 cycle=entry.CaptureCycle()
 for row in raw['samples']:cycle.feed(row)
 assert cycle.complete and raw['samples'][-1]['t_end']-cycle.settle_at>=90
 post=[r for r in raw['samples'] if r['t_end']>=cycle.on_begin]
 stable=[r for r in post if r['t_end']>=cycle.settle_at]
 def native_accepted(r):
  return (r['source_online']==r['acok_online']==1 and r['MaxPower_ma']==500
    and r['source']['current_max_ua']==r['source']['input_current_limit_ua']==500000
    and r['hardware_input']['input_current_limit_ua']==500000
    and r['udc']['state']=='configured')
 def accepted(r):return native_accepted(r) and r['telemetry']['budget_ua']==500000
 assert stable and all(accepted(r) for r in stable)
 assert all(r['telemetry']['valid']==r['telemetry']['protection_ok']==1
  and 0<=r['telemetry']['age_ms']<=3000
  and all(r['telemetry'][k]==0 for k in ['shadow','error','stop_error','latched','fault',
       'source_inhibit','thermal_inhibit','cycle_timeout','gauge_charge_stop']) for r in stable)
 fresh=json.loads((BASE/'charging-management-20261023/usb500-default-r1-private/post-replug-health-stdout-private.json').read_bytes())
 assert fresh['passed'] and fresh['taint']==0 and fresh['R8_camera_notes_unchanged']
 screenshot=json.loads((BASE/'charging-management-20261023/usb500-default-r1-private/screenshot-02-post-replug-private/stdout-private.json').read_bytes())
 screenshot_t={k:int(v) for k,v in (f.split('=') for f in screenshot['telemetry'].split())}
 display=screenshot['upower_text'].split('Device: /org/freedesktop/UPower/devices/DisplayDevice',1)[1].split('Daemon:',1)[0]
 assert screenshot['screenshot_rc']==screenshot['upower_rc']==0
 assert re.search(r'\bstate:\s+charging\b',display)
 assert all(b['status']=='Charging' for b in screenshot['battery'].values())
 image=BASE/'charging-management-20261023/usb500-default-r1-private/screenshot-02-post-replug-private/screen.png'
 report={k:result[k] for k in ['physical_cycle_passed','terminal_reason','sample_count',
  'kernel_event_count','dbus_signal_count','monitor_complete','raw_cycle_evidence','clock_mapping','dbus_parse_errors','edges']}
 report.update(profile='R8 / boot4126 / normal startup500 / retained Image363',
  worker_terminal_absent=True,monitor_cleaned_up=True,identity_unchanged=True,
  source_ACOK_offline_to_online_seconds=cycle.on_begin-cycle.off_begin,
  reconnect_observed_seconds=post[-1]['t_end']-post[0]['t_end'],
  continuous_after_stable_on_seconds=stable[-1]['t_end']-stable[0]['t_end'],
  reconnect_samples=len(post),stable_samples=len(stable),
  native_source_hardware500_all_reconnect_samples=all(native_accepted(r) for r in post),
  native500_and_charger_telemetry_budget_all_reconnect_samples=all(accepted(r) for r in post),
  initial_reconnect_samples=[{k:r[k] for k in ['t_start','t_end','source','hardware_input','udc','battery','telemetry']} for r in post[:3]],
  initial_transient_scope='First online row already has configured/native/source/hardware500 while sequential charger telemetry is valid0/budget0/error-61. Second row budget500 but net discharge; stable-on confirmation and Charging follow. This is a charger sample/startup transient, not evidence of absent native host authorization.',
  native_source_hardware500_all_stable_samples=True,
  stable_instant_current_ua_range=[min(r['telemetry']['gauge_current_ua'] for r in stable),max(r['telemetry']['gauge_current_ua'] for r in stable)],
  stable_positive_instant_samples=sum(r['telemetry']['gauge_current_ua']>0 for r in stable),
  stable_Battery_statuses=sorted({r['battery']['status'] for r in stable}),
  fresh_postcheck=fresh,
  screenshot=dict(sha256=sha(image.read_bytes()),charging_lightning_visually_present=True,
                  Battery=screenshot['battery'],instant_current_ua=screenshot_t['gauge_current_ua'],UPower_charging=True),
  human_feedback='已接好，图标明显更快',screen_subjectively_improved=True,
  screen_pixel_latency_measured=False,cold_boot_accepted=False,PM_accepted=False,
  raw_sha256=sha((CAPTURE/'capture-private.json').read_bytes()),
  scope='One real same-port computer data-cable detach/attach, continuous native500 and net charging, endpoint-estimated notification timing, later screenshot and qualitative human feedback. No pixel timing SLA or all-mode acceptance.',
  event_timing_reference='source_uevent_t; Display State2=discharging and State1=charging are actual observed transitions; clock-mapped estimates are not physical-plug or screen-frame timestamps.')
 (REF/'icon-r8-eud-off-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:report[k] for k in ['physical_cycle_passed','reconnect_observed_seconds',
  'continuous_after_stable_on_seconds','stable_samples','native_source_hardware500_all_reconnect_samples',
  'stable_instant_current_ua_range','stable_positive_instant_samples','stable_Battery_statuses','screen_subjectively_improved']}))

if __name__=='__main__':main()
