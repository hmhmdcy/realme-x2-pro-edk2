"""One failed-disconnect return against Image503 gadget plus frozen SUSPHY core."""
from pathlib import Path
import difflib
import hashlib
import json
import re
HERE=Path(__file__).resolve().parent
REF=HERE.parents[1]
OLD=REF/'charging-session-20261023/dwc-device-start-recovery-candidate'
CORE=HERE.parent/'dwc-pm-error-unwind-candidate'
sha=lambda raw:hashlib.sha256(raw).hexdigest()


def function(text,name):
    match=re.search(r'^(?:static\s+)?(?:int|void|bool|irqreturn_t)\s+'+name+r'\([^;]*?\)\s*\{',text,re.M)
    assert match is not None,name
    pos=text.index('{',match.start());end=pos+1;depth=1
    while depth:
        depth+=(text[end]=='{')-(text[end]=='}');end+=1
    return text[match.start():end]


def main():
    original=(OLD/'gadget.c').read_bytes();core=(CORE/'core.c').read_bytes();header=(OLD/'core.h').read_bytes()
    assert sha(original)=='ca4bf1c5a1afa42267d2f7f8b636dfe7ca5a1b9581307093f93a892e2f004314'
    assert sha(core)=='5331ae946cde894e2da484df5b8fbc6d386d117a60ad0e3dac5a1ebaaec6a17f'
    assert sha(header)=='9a8dc48a1283db17b6a0cad01f0bc43ff916cfa7dc3a11b680c2145984f97a67'
    text=original.decode();oldfn=function(text,'dwc3_gadget_suspend')
    token='\t\tdwc3_gadget_soft_connect(dwc);\n\t\treturn -EAGAIN;\n\t}\n'
    assert oldfn.count(token)==1
    newfn=oldfn.replace(token,token+'\t/* Without a requested reconnect, preserve the failed stop errno.\n'
        '\t * The core must keep its resources active until HALT is proven.\n'
        '\t */\n\tif (ret)\n\t\treturn ret;\n')
    candidate=text.replace(oldfn,newfn)
    assert candidate.replace(newfn,oldfn)==text
    (HERE/'gadget.c').write_text(candidate,newline='\n')
    patch=''.join(difflib.unified_diff(text.splitlines(True),candidate.splitlines(True),
          fromfile='Image503/drivers/usb/dwc3/gadget.c',tofile='candidate/drivers/usb/dwc3/gadget.c'))
    (HERE/'suspend-halt-error.patch').write_text(patch,newline='\n')
    coretext=core.decode()
    gadget_names=['dwc3_gadget_run_stop','dwc3_gadget_disable_irq','__dwc3_gadget_ep_disable',
                  '__dwc3_gadget_stop','dwc3_gadget_soft_disconnect','dwc3_gadget_suspend']
    core_names=['dwc3_enable_susphy','dwc3_suspend_common','dwc3_runtime_checks',
                'dwc3_runtime_suspend','dwc3_pm_suspend']
    funcs={name:function(candidate,name) for name in gadget_names}
    funcs.update({name:function(coretext,name) for name in core_names})
    special=coretext[coretext.index('/* Stack-only ownership of SUSPHY'):coretext.index('static int dwc3_suspend_common')]
    order=['dwc3_gadget_run_stop','dwc3_gadget_disable_irq','__dwc3_gadget_ep_disable',
           '__dwc3_gadget_stop','dwc3_gadget_soft_disconnect','dwc3_gadget_suspend','dwc3_enable_susphy']
    extracted='\n\n'.join(funcs[name] for name in order)+'\n\n'+special+'\n\n'
    extracted+='\n\n'.join(funcs[name] for name in core_names[1:])+'\n'
    (HERE/'tested-functions.inc').write_text(extracted,newline='\n')
    previous=oldfn.replace('dwc3_gadget_suspend(','previous_gadget_suspend(',1)
    previous+='\n\n'+funcs['dwc3_suspend_common'].replace('dwc3_suspend_common(','previous_suspend_common(',1).replace('dwc3_gadget_suspend(','previous_gadget_suspend(')+'\n'
    (HERE/'previous-functions.inc').write_text(previous,newline='\n')
    evidence_names=['dwc3_gadget_run_stop','dwc3_gadget_soft_disconnect','__dwc3_gadget_stop',
          '__dwc3_gadget_ep_disable','dwc3_remove_requests','dwc3_stop_active_transfers',
          'dwc3_thread_interrupt','dwc3_process_event_buf','dwc3_disconnect_gadget_sleepable']
    evidence={name:dict(sha256=sha(function(text,name).encode()),line=text[:text.index(function(text,name))].count('\n')+1)
              for name in evidence_names}
    result=dict(passed=True,inputs={'gadget.c':sha(original),'core.c':sha(core),'core.h':sha(header)},
        candidate_gadget_sha256=sha(candidate.encode()),changed_existing_functions=['dwc3_gadget_suspend'],
        original_softconnect_true_policy_unchanged=True,core_and_header_unchanged=True,
        actual_function_sha256={name:sha(body.encode()) for name,body in funcs.items()},
        frozen_core_susphy_block_sha256=sha(special.encode()),lifetime_source_evidence=evidence,
        full_resume_error_unwind_complete=False,Halt_proven_by_negative_return=False,
        existing_later_pullups_false_retry_gap_not_fixed=True)
    (HERE/'source-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(prepared=True,gadget_sha256=result['candidate_gadget_sha256'])))


if __name__=='__main__':main()
