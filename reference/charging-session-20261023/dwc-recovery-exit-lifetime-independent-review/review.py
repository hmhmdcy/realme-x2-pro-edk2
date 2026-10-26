"""Read/hash/compare the frozen author source and receipts. No author execution."""
from pathlib import Path
import difflib
import hashlib
import json
import re
import sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
AUTHOR = REF/'charging-ui-audit-20261023/dwc-recovery-exit-lifetime-candidate'
BASE = REF/'charging-session-20261023/dwc-device-resume-outcome-candidate'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def function(text,name):
    start = re.search(r'^(?:static\s+)?(?:inline\s+)?(?:int|void|bool|irqreturn_t)\s+'+
                      name+r'\([^;]*?\)\s*(?:__must_hold\([^\n]*\)\s*)?\{', text, re.M)
    assert start, name
    end = text.index('{',start.start())+1
    depth = 1
    while depth:
        depth += (text[end]=='{')-(text[end]=='}')
        end += 1
    return text[start.start():end]


def main():
    if sys.flags.optimize:
        raise RuntimeError('nonoptimized independent source review required')
    assert sha(AUTHOR/'source-delivery.json') == '4a645839ece5fd0273b3ff93beda9616593e94dc69215e9822295c76b6f26f07'
    delivery = json.loads((AUTHOR/'source-delivery.json').read_bytes())
    assert delivery['passed'] and delivery['frozen'] and len(delivery['files'])==13
    for name,item in delivery['files'].items():
        assert sha(AUTHOR/name)==item['sha256'] and (AUTHOR/name).stat().st_size==item['bytes'],name
    tests = json.loads((AUTHOR/'test-result.json').read_bytes())
    assert tests['passed'] and tests['summary']['cases']==8
    for name,digest in tests['files'].items():
        assert sha(AUTHOR/name)==digest,name
    assert [p['pid'] for p in tests['phases']]==[788,797]
    assert all(p['terminal'] and p['returncode']==0 for p in tests['phases'])
    source = json.loads((AUTHOR/'source-result.json').read_bytes())
    for name,digest in source['source_inputs'].items():
        assert sha(REF/name)==digest,name
    g,h = [(AUTHOR/n).read_text() for n in ['gadget.c','core.h']]
    oldg,oldh = [(BASE/n).read_text() for n in ['gadget.c','core.h']]
    changed = ['dwc3_schedule_err_recovery','dwc3_gadget_recover_locked','dwc3_gadget_init','dwc3_gadget_exit']
    rebuilt = oldg
    for name in changed:
        before,after = function(oldg,name),function(g,name)
        assert rebuilt.count(before)==1
        rebuilt = rebuilt.replace(before,after)
    assert rebuilt==g, 'Only the four actual function bodies change'
    assert h.replace(' * @recovery_stopping: exit-only recovery enqueue gate, protected by lock\n','').replace(
        '\t/* Only gadget init reopens this exit-owned producer gate. */\n\tbool\t\t\trecovery_stopping;\n','')==oldh
    patch = ''.join(difflib.unified_diff(oldg.splitlines(True),g.splitlines(True),
        fromfile='a/drivers/usb/dwc3/gadget.c',tofile='b/drivers/usb/dwc3/gadget.c'))
    patch += ''.join(difflib.unified_diff(oldh.splitlines(True),h.splitlines(True),
        fromfile='a/drivers/usb/dwc3/core.h',tofile='b/drivers/usb/dwc3/core.h'))
    assert patch==(AUTHOR/'recovery-exit-lifetime.patch').read_text()
    for name,digest in source['unchanged_functions'].items():
        body = function(g,name)
        assert body==function(oldg,name) and hashlib.sha256(body.encode()).hexdigest()==digest,name
    actual = (AUTHOR/'actual-functions.inc').read_text()
    for name in ['dwc3_schedule_err_recovery','dwc3_gadget_recover_locked','dwc3_err_recovery_work',
                 'dwc3_gadget_pullup','dwc3_gadget_stop','dwc3_gadget_exit']:
        assert function(g,name)==function(actual,name),name
    schedule = function(g,'dwc3_schedule_err_recovery')
    helper = function(g,'dwc3_gadget_recover_locked')
    exit_body = function(g,'dwc3_gadget_exit')
    init = function(g,'dwc3_gadget_init')
    assert len(re.findall(r'\bschedule_work\(&dwc->err_recovery_work\)',g))==2
    assert 'if (!dwc->recovery_stopping)\n\t\tschedule_work' in schedule
    assert 'if (result->pending && !dwc->recovery_stopping)\n\t\tschedule_work' in helper
    assert helper.index('result->reconnected = false;') < helper.index('if (dwc->recovery_stopping)')
    assert helper.index('if (dwc->recovery_stopping)') < helper.index('result->stage = "disconnect";')
    assert helper.rindex('schedule_work(') < helper.rindex('spin_unlock_irqrestore(')
    exit_code = re.sub(r'/\*.*?\*/','',exit_body,flags=re.S)
    order = ['spin_lock_irqsave(','dwc->recovery_stopping = true;','spin_unlock_irqrestore(',
             'cancel_work_sync(','dwc3_enable_susphy(','usb_del_gadget(','mutex_destroy(',
             'dwc3_gadget_free_endpoints(']
    assert [exit_code.index(n) for n in order]==sorted(exit_code.index(n) for n in order)
    assert not re.search(r'\bmutex_lock\s*\(',exit_code)
    assert init.index('dwc->recovery_stopping = false;') < init.index('INIT_WORK(') < init.index('usb_add_gadget(')
    assert len(re.findall(r'dwc->recovery_stopping\s*=',g))==2
    evidence = json.loads((AUTHOR/'caller-source-evidence.json').read_bytes())
    for name,item in evidence['sources'].items():
        p = REF/name
        assert sha(p)==item['sha256'] and p.stat().st_size==item['bytes'],name
        text = p.read_text()
        for fun,row in item['functions'].items():
            body = function(text,fun)
            assert hashlib.sha256(body.encode()).hexdigest()==row['sha256'],fun
            assert text[:text.index(body)].count('\n')+1==row['line'],fun
    udcpath = REF/'charging-oem-audit-20261023/usb-resume-errors/drivers--usb--gadget--udc--core.c'
    udc = udcpath.read_text()
    assert 'device_del(&gadget->dev);' in function(udc,'usb_del_gadget')
    assert '.remove = gadget_unbind_driver,' in udc
    unbind = function(udc,'gadget_unbind_driver')
    udc_order=['cancel_work_sync(&udc->vbus_work);','usb_gadget_disconnect_locked(gadget);',
        'usb_gadget_disable_async_callbacks(udc);','udc->driver->unbind(gadget);','usb_gadget_udc_stop_locked(udc);']
    assert [unbind.index(n) for n in udc_order]==sorted(unbind.index(n) for n in udc_order)
    assert 'gadget->ops->pullup(gadget, 0)' in function(udc,'usb_gadget_disconnect_locked')
    assert 'udc->gadget->ops->udc_stop(udc->gadget)' in function(udc,'usb_gadget_udc_stop_locked')
    assert 'free_irq(dwc->irq_gadget, dwc->ev_buf);' in function(g,'dwc3_gadget_stop')
    result = dict(passed=True,status='accepted_within_exit_only_source_scope',confirmed_new_findings=[],
        author_source_delivery_sha256=sha(AUTHOR/'source-delivery.json'),
        author_test_receipt_sha256=sha(AUTHOR/'test-result.json'),
        author_caller_evidence_sha256=sha(AUTHOR/'caller-source-evidence.json'),
        checked_author_files={n:item['sha256'] for n,item in delivery['files'].items()},
        exact_changed_functions=changed,unchanged_functions_checked=len(source['unchanged_functions']),
        actual_fixture_functions_checked=6,new_author_cases_read_not_run=8,
        both_enqueue_sites_serialized_with_exit_gate=True,cancel_join_outside_spin_and_connect_mutex=True,
        connect_mutex_outlives_bound_UDC_unbind_and_IRQ_release=True,
        generic_bus_dd_basis='existing synchronous device_del/bus-remove API; cached UDC/remove and device_del inspected',
        callback_scope_reused='fixed-source configfs/NCM DWC R2 review, not arbitrary future function drivers',
        future_producers_excluded_only_for_recovery_work=True,full_PM_abort_or_HALT_proved=False,
        persistent_struct_layout_change_requires_consistent_rebuild=True,
        author_entrypoints_imported_or_executed=False,tests_rerun=False,kernel_compiled=False,
        storage_helper_device_SSH_USB_SDK_Git_used=False,
        review_files={n:sha(HERE/n) for n in ['README.md','review.py']})
    (HERE/'review-result.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    print(json.dumps(dict(passed=True,review_result_sha256=sha(HERE/'review-result.json'),
                         unchanged_functions_checked=result['unchanged_functions_checked'])))


if __name__=='__main__':
    main()
