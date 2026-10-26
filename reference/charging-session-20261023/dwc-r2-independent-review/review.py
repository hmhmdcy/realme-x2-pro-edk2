"""Hash/static checks only. Does not import or run frozen authors' helpers."""
from pathlib import Path
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
AUDIT = HERE.parents[1] / 'charging-oem-audit-20261023'
R1 = AUDIT / 'apsd-dwc-window-candidate'
R2 = AUDIT / 'apsd-dwc-window-candidate-r2'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
delivery = json.loads((R2 / 'delivery.json').read_text())
for name, digest in delivery['files'].items():
    assert sha(R2 / name) == digest, name
old = (R1 / 'gadget.c').read_text()
expected = old.replace('if (dwc->detect_stopping) {',
                       'if (dwc->detect_stopping && is_on) {', 1)
before = 'if (dwc3_gadget_window_busy(dwc) || READ_ONCE(dwc->detect_stopping)) {'
after = 'if (dwc3_gadget_window_busy(dwc) ||\n\t    (READ_ONCE(dwc->detect_stopping) && is_on)) {'
assert expected.count(before) == 1
expected = expected.replace(before, after)
assert expected == (R2 / 'gadget.c').read_text()
for name in ['core.c', 'core.h', 'window-functions.c.txt']:
    assert (R1 / name).read_bytes() == (R2 / name).read_bytes()
f1 = {row['function']: row['sha256'] for row in json.loads((R1 / 'tested-functions.json').read_text())}
f2 = {row['function']: row['sha256'] for row in json.loads((R2 / 'tested-functions.json').read_text())}
assert f1.keys() == f2.keys()
assert [name for name in f1 if f1[name] != f2[name]] == ['dwc3_gadget_pullup']
prior = json.loads((R2 / 'test-result.json').read_text())
assert prior['passed'] and prior['groups_count'] == 5 and not prior['original_13_groups_rerun']
failure = json.loads((R2 / 'r1-failure-review.json').read_text())
assert failure['case'] == {'reproduced': True, 'active_window': False, 'pullup_off_errno': -108,
                          'soft_disconnect_calls': 0, 'halt_established': False, 'irq_freed': True}


def function(path, name):
    text = path.read_text()
    match = re.search(r'^(?:static\s+)?[\w\s*]+?\b' + name + r'\([^;]*?\)\n\{', text, re.M)
    assert match, name
    a = match.start()
    while text[a] == '\n':
        a += 1
    body = text[a:text.index('\n}', match.end()) + 2]
    return {'file': str(path), 'function': name, 'line': text.count('\n', 0, a) + 1,
            'sha256': hashlib.sha256(body.encode()).hexdigest(), 'body': body}


udc = AUDIT / 'apsd-integration/current-r7/extra-snapshots/drivers--usb--gadget--udc--core.c'
rows = [function(udc, 'gadget_unbind_driver')]
body = rows[0]['body']
assert body.index('usb_gadget_disconnect_locked(gadget)') < body.index('usb_gadget_udc_stop_locked(udc)')
for name in ['dwc3_gadget_exit', 'dwc3_gadget_stop', 'dwc3_gadget_pullup',
             'dwc3_gadget_window_shutdown', 'dwc3_interrupt', 'dwc3_check_event_buf',
             'dwc3_thread_interrupt', 'dwc3_process_event_buf', 'dwc3_process_event_entry',
             'dwc3_gadget_interrupt', 'dwc3_disconnect_gadget', 'dwc3_disconnect_gadget_sleepable',
             'dwc3_schedule_err_recovery', 'dwc3_err_recovery_work', 'dwc3_gadget_recover_locked']:
    rows.append(function(R2 / 'gadget.c', name))
for name in ['dwc3_suspend_common', 'dwc3_resume_common', 'dwc3_pm_prepare', 'dwc3_pm_complete']:
    rows.append(function(R2 / 'core.c', name))
for row in rows:
    if row['function'] in ['dwc3_interrupt', 'dwc3_check_event_buf', 'dwc3_thread_interrupt',
                           'dwc3_process_event_buf', 'dwc3_process_event_entry', 'dwc3_gadget_interrupt',
                           'dwc3_schedule_err_recovery']:
        assert 'connect_mutex' not in row['body']
        assert not any(call in row['body'] for call in ['flush_work(', 'cancel_work_sync(',
                                                       'flush_scheduled_work('])
    row.pop('body')
sources = json.loads((HERE / 'callback-source-manifest.json').read_text())
for row in sources:
    assert row['byte_equal_to_image_source_commit'] and sha(HERE / row['snapshot']) == row['sha256']
for name in ['source--drivers--usb--gadget--function--f_ncm.c',
             'source--drivers--usb--gadget--function--u_ether.c']:
    text = (HERE / name).read_text()
    assert not any(call in text for call in ['usb_gadget_connect(', 'usb_gadget_disconnect(',
                                           'usb_gadget_activate(', 'usb_gadget_deactivate('])

result = {'review_complete': True, 'confirmed_new_issues': [],
          'reviewed_r2_delivery_sha256': sha(R2 / 'delivery.json'),
          'reviewed_r2_patch_sha256': sha(R2 / 'dwc-window.patch'),
          'all_frozen_delivery_hashes_match': True,
          'r1_to_r2_exactly_two_conditions': True,
          'unchanged_tested_function_bodies': 19, 'changed_tested_function': 'dwc3_gadget_pullup',
          'r1_no_window_teardown_failure_reused': True,
          'r2_five_case_receipt_reused_sha256': sha(R2 / 'test-result.json'),
          'irq_connect_mutex_reverse_path_proven': False,
          'manual_callback_scope': 'Image-associated configfs composite/NCM, EP0 and gether callbacks; no arbitrary future gadget-function claim',
          'reviewed_functions': rows,
          'new_c_function_tests_executed': False, 'original_13_groups_rerun': False,
          'existing_five_groups_rerun': False, 'kernel_build_invoked': False,
          'phone_accessed': False, 'ssh_executed': False, 'usb_accessed': False,
          'sdk_invoked': False, 'shared_source_modified': False, 'frozen_candidate_modified': False,
          'scope': 'independent source/call-chain review plus reused exact-byte receipts; no lockdep or hardware proof'}
(HERE / 'review-result.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
print(json.dumps({key: value for key, value in result.items() if key != 'reviewed_functions'}, indent=2))
