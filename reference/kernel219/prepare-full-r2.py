from pathlib import Path
import host,json,shutil

here=Path(__file__).resolve().parent
assert json.loads((here/'full-mode-finish-validation.json').read_text())['experimental_full_raw_disabled']
shutil.copyfile(host.PRIVATE/'transport-last-failure-private.log',host.PRIVATE/'full-initial-preflight-private.log')
code=r'''
from pathlib import Path
import json
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k219-runtime/boot-id-private.txt').read_bytes()
p=root/'k219-capture-4608x3456-raw-pattern0-system';dest=p.with_name(p.name+'-preflight-not-idle')
assert p.is_dir() and not p.is_symlink() and not any(p.iterdir()) and not dest.exists()
assert Path('/sys/module/imx471/parameters/unprocessed_fullres').read_text().strip()=='N'
p.rename(dest);(dest/'preflight-failure.json').write_text(json.dumps(dict(no_capture_started=True,preflight_failed_on_runtime_suspend=True,original_default_flag_and_policy_restored=True))+'\n')
print('First preflight retained; no capture had started and the default driver flag was restored')
'''
p=host.ssh('python3 -',input=code.encode(),timeout=30);print(p.stdout.decode().strip())
source=(here/'run-full-experiment.py').read_text()
source=source.replace("controller=(here/'full-mode-control.py').read_text()","controller=(here/'full-mode-control.py').read_text().replace(\"out=root/'k219-full-mode-experiment'\",\"out=root/'k219-full-mode-experiment-r2'\")")
source=source.replace("'full-mode-'+phase","'full-mode-r2-'+phase")
assert not (here/'run-full-experiment-r2.py').exists();(here/'run-full-experiment-r2.py').write_text(source)
report=dict(stage=219,initial_full_mode_capture_not_started=True,post_probe_runtime_suspend_not_yet_completed=True,
            original_module_flag_and_policy_restored=True,proper_bounded_runtime_suspend_wait_added=True,initial_preflight_logs_preserved=True)
(here/'full-initial-preflight-validation.json').write_text(json.dumps(report,indent=2)+'\n')
