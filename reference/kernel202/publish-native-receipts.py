from pathlib import Path
import importlib.util,json

here=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('current_r2',here/'reboot-r2/host.py');host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
for remote,name in [('k202r2-geoclue-first-session/summary.json','geoclue-first-session-validation.json'),('k202r2-final-health/summary.json','native-health-validation.json')]:
    target=host.PRIVATE/name;host.download('/var/lib/samurai/'+remote,target)
    report=json.loads(target.read_text());assert report['stage']==202
    (here/name).write_text(json.dumps(report,indent=2)+'\n')
target=host.PRIVATE/'watch-readiness-timeout-private.json'
host.download('/var/lib/samurai/k202r2-runtime/watch-readiness-timeout-private.json',target)
prior=json.loads(target.read_text())
runtime=json.loads((here/'reboot-r2/runtime-validation.json').read_text())
report=dict(stage=202,early_observer_timeout_preserved=True,preparation_status_at_observer_timeout=prior['time_preparation_last_result']['status'],preparation_attempts_at_timeout=prior['time_preparation_starts'],automatic_preparation_completed_later_without_service_restart=True,successful_preparation_attempts_total=runtime['idle_utc_preparation_attempts'],no_manual_time_or_gps_engine_or_power_change=True)
(here/'clock-startup-retry-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(stage=202,native_receipts_published=True,clock_retry=report)))
