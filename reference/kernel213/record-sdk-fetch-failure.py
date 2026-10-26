from pathlib import Path
import json
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel213');path=here/'sdk-fetch-validation.json'
original=path.read_bytes();(private/'sdk-fetch-original-empty-report-private.json').write_bytes(original)
assert json.loads(original)['signed_apks']==[]
assert 'libglvnd-dev (no such package)' in (private/'sdk-fetch-private.log').read_text()
report=dict(stage=213,first_sdk_fetch_failed=True,missing_package='libglvnd-dev',downloaded_packages=0,initial_script_failed_to_reject_apk_error_and_empty_output=True,original_report_and_error_log_retained_privately=True,no_phone_install_or_product_change=True,corrected_fetch_requires_no_error_and_all_requested_packages=True)
(here/'sdk-fetch-first-failure-validation.json').write_text(json.dumps(report,indent=2)+'\n');path.write_text(json.dumps(dict(stage=213,all_signatures_verified=False,sdk_fetch_complete=False,see='sdk-fetch-first-failure-validation.json'),indent=2)+'\n')
print('Empty SDK result rejected and original evidence preserved; corrected package fetch required.')
