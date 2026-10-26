"""Offline semantic/budget audit only; no event-latency reanalysis or device IO."""
from pathlib import Path
import hashlib,json,re
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
fetch=Path('/mnt/e/edk2-samurai-out/charging-oem-audit-20261023/usbin-init-host/usbin-init-r8-003/fetch-1792764030744355505')
build_path=REF/'charging-management-20261023/thermal-bands-build-result.json'
build=json.loads(build_path.read_text());assert build['passed']
r8=Path('/home/cy122/charging-management-20261023/thermal-bands-candidate/source-view/drivers/power/supply/samurai-mp2650.c')
assert sha(r8)==build['sources']['samurai-mp2650.c']=='ed2e1d4d96ea4f2d55b514288b0e8da1d731864d385944d02a105d41b03a144c'
entry=REF/'charging-session-20261023/r8-source-integration'
entry_manifest=json.loads((entry/'source-manifest.json').read_text())
charger_row=entry_manifest['sources']['drivers/power/supply/samurai-mp2650.c']
entry_charger=entry/'kernel-sources/drivers/power/supply/samurai-mp2650.c'
entry_origin=REF/charger_row['origin']
assert entry_charger.read_bytes()==entry_origin.read_bytes()==r8.read_bytes()
assert charger_row['sha256']==sha(r8)
text=r8.read_text();lines=text.splitlines()
ranges=[(286,327),(424,444),(501,517),(683,704)]
(HERE/'r8-status-excerpts.txt').write_text('\n'.join(f'{i+1}: {lines[i]}' for a,b in ranges for i in range(a-1,b))+'\n')
samples_path=fetch/'capture/samples-private.jsonl';rows=[json.loads(s) for s in samples_path.read_text().splitlines()]
qualified=[]
for index,row in enumerate(rows):
 h=row.get('helper',{}).get('state',{});t=row.get('telemetry',{});raw=row.get('raw_pmic',[])
 if h.get('phase')=='clear_verified' and h.get('before_cfg')==192 and h.get('after_cfg')==64 and h.get('write_return')==0 and not h.get('unknown_write') and len(raw)==8 and raw[7]==64 and row.get('source_online')==1 and row.get('acok_online')==1 and t.get('valid')==1 and t.get('age_ms',999999)<=2500:
  qualified.append((index,row))
assert qualified
def distinct(fn):return sorted({fn(r) for _,r in qualified})
battery_current=[r['battery']['current_now_ua'] for _,r in qualified]
gauge_current=[r['telemetry']['gauge_current_ua'] for _,r in qualified]
summary=dict(count=len(qualified),row_indices_zero_based=[i for i,_ in qualified],
 source_online=distinct(lambda r:r['source_online']),acok_online=distinct(lambda r:r['acok_online']),
 usb_type=distinct(lambda r:r['source']['usb']['usb_type']),
 effective_ua=distinct(lambda r:r['source']['usb']['current_max']),native_ua=distinct(lambda r:r['source']['usb']['input_current_limit']),
 programmed_iin_ua=distinct(lambda r:r['source']['charger']['input_current_limit']),
 programmed_cc_ua=distinct(lambda r:r['source']['charger']['constant_charge_current']),
 programmed_cv_uv=distinct(lambda r:r['source']['charger']['constant_charge_voltage']),
 charger_status=distinct(lambda r:r['source']['charger']['status']),battery_status=distinct(lambda r:r['battery']['status']),
 battery_current_now_ua_range=[min(battery_current),max(battery_current)],
 gauge_instant_ua_range=[min(gauge_current),max(gauge_current)],
 raw_PMIC_first7=[list(x) for x in sorted({tuple(r['raw_pmic'][:7]) for _,r in qualified})],
 desired_enable=distinct(lambda r:r['telemetry']['desired_enable']),protection_ok=distinct(lambda r:r['telemetry']['protection_ok']),
 fault=distinct(lambda r:r['telemetry']['fault']),latched=distinct(lambda r:r['telemetry']['latched']),
 thermal_inhibit=distinct(lambda r:r['telemetry']['thermal_inhibit']),logical_full=distinct(lambda r:r['telemetry']['logical_full']))
assert summary['native_ua']==summary['effective_ua']==summary['programmed_iin_ua']==[100000]
assert summary['battery_status']==['Discharging'] and max(battery_current)<0
assert summary['charger_status']==['Charging'] and summary['protection_ok']==[1] and summary['latched']==summary['fault']==[0]
files=[samples_path,fetch/'capture/config-private.json',build_path,entry/'source-manifest.json',entry/'delivery.json',entry_charger,entry_origin,
 REF/'charging-ui-audit-20261023/kernel-bq27xxx_battery.c',REF/'charging-ui-audit-20261023/upower-up-device-supply-battery.c',
 REF/'charging-ui-audit-20261023/phosh-battery-manager.c',REF/'charging-ui-audit-20261023/upower-up-daemon.c',HERE.parent/'icon-semantics/test-result.json',
 HERE.parent/'usb500-r7-trial-audit/usb500-r7-result.json',HERE.parent/'eud-sdp500/cached-node-result.json',
 HERE.parent/'eud-boot-policy-r2/candidate-result.json']
result=dict(passed=True,scope='cached R8 power-flow semantics and permitted budget only; no latency recomputation',
 raw_files=[dict(path=str(p),sha256=sha(p)) for p in files],R8_actual_compiled_source=dict(path=str(r8),sha256=sha(r8)),
 R8_module_sha256=build['module_sha256'],current_public_source_not_substituted_for_compiled_R8=True,
 current_R8_public_integration_entry_verified=dict(path=str(entry_charger),origin=str(entry_origin),sha256=sha(entry_charger),byte_equal_to_actual_private_compiled_source=True),
 sample_rows=len(rows),qualified_postclear_power_flow=summary,
 current_MaxPower_read_in_this_capture=False,current_host_configuration_descriptor_read_in_this_capture=False,
 conclusions={'bit7_alone_upgrades_same_port_to_CDP_or_native500':False,'SDP100_budget_bypass_justified':False,
 'charger_status_is_net_battery_current':False,'battery_Discharging_with_negative_current_is_semantically_consistent':True,
 'hub_power_refusal_proven_by_old_500_trial':False,'charging_icon_fix_proven':False},
 proposed_next_offline='bind already-frozen boot-only EUD-off R2 full firmware inputs/payload to unchanged Image363/native DTB/camera ABI and independent review; no build/deploy assumed',
 independent_next_physical_variable='if separately authorized later: verify real EUD-off/readback/no-producers and changed data topology with existing100; no repeated500 trial here',
 UI_timing_audit_delegated_separately=True,old_suites_rerun=False,phone_accessed=False,ssh_executed=False,USB_accessed=False,SDK_invoked=False,Git_invoked=False)
(HERE/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(passed=True,qualified_rows=len(qualified),battery_current_range=summary['battery_current_now_ua_range'],
 instant_range=summary['gauge_instant_ua_range'],native=summary['native_ua'],result_sha256=sha(HERE/'result.json')),indent=2))
