"""Extract only actual device-resume and caller bodies for the new failure."""
from pathlib import Path
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
AUDIT = HERE.parents[1] / 'charging-oem-audit-20261023'
CANDIDATE = AUDIT / 'apsd-dwc-resume-error-candidate'
R2 = AUDIT / 'apsd-dwc-window-candidate-r2'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(CANDIDATE / 'core.c') == 'cdff700a415cfa0de231dded3b00b18a31aae23de19dd4a894c894517bc06e2d'
assert sha(R2 / 'gadget.c') == '0153f79691ef73473e791341c710d092421213cffbd5fbe07411a00037daa07a'
core = (CANDIDATE / 'core.c').read_text()
gadget = (R2 / 'gadget.c').read_text()


def function(text, name):
    m = re.search(r'^(?:static )?(?:int|void) ' + name + r'\([^;]*?\)\n\{', text, re.M)
    assert m, name
    return text[m.start():text.index('\n}', m.end()) + 2]


names = [(core, 'dwc3_clk_enable'), (core, 'dwc3_clk_disable'),
         (core, 'dwc3_core_exit'), (core, 'dwc3_core_init_for_resume'),
         (gadget, 'dwc3_gadget_soft_connect'), (gadget, 'dwc3_gadget_resume'),
         (core, 'dwc3_resume_common'), (core, 'dwc3_runtime_resume'), (core, 'dwc3_pm_resume')]
actual = '\n\n'.join(function(text, name) for text, name in names) + '\n'
(HERE / 'actual-functions.inc').write_bytes(actual.encode())
runtime = (HERE / 'source--drivers--base--power--runtime.c').read_text()
assert '__update_runtime_status(dev, RPM_SUSPENDED);\n\t\tpm_runtime_cancel_pending(dev);' in runtime
assert 'retval = rpm_callback(callback, dev);' in runtime
result = {'core_sha256': sha(CANDIDATE / 'core.c'), 'gadget_r2_sha256': sha(R2 / 'gadget.c'),
          'actual_function_names': [name for text, name in names],
          'actual_functions_sha256': sha(HERE / 'actual-functions.inc'),
          'root_test_receipt_sha256': sha(CANDIDATE / 'test-result.json'),
          'root_build_receipt_sha256': sha(CANDIDATE / 'build-result.json'),
          'source_manifest_sha256': sha(HERE / 'source-manifest.json'),
          'root_candidate_modified': False, 'old_suites_rerun': False}
(HERE / 'extraction-result.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
print(json.dumps(result, indent=2))
