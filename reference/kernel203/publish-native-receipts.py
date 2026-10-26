from pathlib import Path
import json
import host

here=Path(__file__).resolve().parent
for remote,name in [
 ('k203-package-install/summary.json','package-install-validation.json'),
 ('k203-packaged-helper/summary.json','packaged-helper-validation.json'),
 ('k203-geoclue-package-test/summary.json','geoclue-package-validation.json'),
 ('k203-final-health/summary.json','native-health-validation.json')]:
 target=host.PRIVATE/name;host.download('/var/lib/samurai/'+remote,target)
 report=json.loads(target.read_text());assert report['stage']==203
 if 'same_verified_new_boot' in report:
  report['same_verified_current_boot']=report.pop('same_verified_new_boot')
  assert report['same_boot202r2'] and report['new_reboot_not_performed']
 (here/name).write_text(json.dumps(report,indent=2)+'\n')
initial=json.loads((host.PRIVATE/'transport-probes-private.json').read_text())
final=json.loads((host.PRIVATE/'transport-probes-final-private.json').read_text())
report=dict(stage=203,initial_usb_responsive=initial['transports']['usb']['responsive'],
 initial_wifi_current_boot_verified=initial['transports']['wifi']['current203_boot_verified'],
 final_usb_current_boot_verified=final['transports']['usb']['current203_boot_verified'],
 final_wifi_current_boot_verified=final['transports']['wifi']['current203_boot_verified'],
 usb_bulk_copy_stalled=True,partial_copy_preserved_and_not_used=True,
 full_candidate_recovered_over_authenticated_wifi=True,
 no_usb_reset_unbind_or_reboot=True,small_probe_recovery_does_not_prove_bulk_stability=True)
(here/'transport-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(stage=203,native_receipts_published=True,transport=report)))
