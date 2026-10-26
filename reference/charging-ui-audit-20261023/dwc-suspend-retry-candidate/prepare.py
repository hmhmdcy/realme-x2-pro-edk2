"""Derive a readonly active no-pullup HALT gate from the frozen errno fix."""
from pathlib import Path
import difflib,hashlib,json,re
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
OLD=HERE.parent/'dwc-suspend-halt-error-candidate'
CORE=HERE.parent/'dwc-pm-error-unwind-candidate'
HEADER=REF/'charging-session-20261023/dwc-device-start-recovery-candidate/core.h'
sha=lambda raw:hashlib.sha256(raw).hexdigest()


def function(text,name):
 match=re.search(r'^(?:static\s+)?(?:int|void|bool|irqreturn_t)\s+'+name+r'\([^;]*?\)\s*\{',text,re.M)
 assert match is not None,name
 pos=text.index('{',match.start());end=pos+1;depth=1
 while depth:depth+=(text[end]=='{')-(text[end]=='}');end+=1
 return text[match.start():end]


def main():
 original=(OLD/'gadget.c').read_bytes();core=(CORE/'core.c').read_bytes();header=HEADER.read_bytes()
 assert sha(original)=='aabfc928ca916d5b40492996153a03c08b837dcbb1d0c07091f23a35c2debfe2'
 assert sha(core)=='5331ae946cde894e2da484df5b8fbc6d386d117a60ad0e3dac5a1ebaaec6a17f'
 assert sha(header)=='9a8dc48a1283db17b6a0cad01f0bc43ff916cfa7dc3a11b680c2145984f97a67'
 text=original.decode();oldfn=function(text,'dwc3_gadget_suspend')
 token='\tint ret;\n\n'
 assert oldfn.count(token)==1
 gate='''\tunsigned long flags;
\tu32 reg;
\tint ret;

\t/* A previous stop can clear the software pullup flag before HALT.
\t * Do not repeat request teardown or reset while waiting for that HALT.
\t * This is a hardware snapshot, not serialization of every run/stop
\t * writer through the subsequent core PM exit.
\t */
\tspin_lock_irqsave(&dwc->lock, flags);
\tif (!dwc->pullups_connected && !pm_runtime_suspended(dwc->dev)) {
\t\treg = dwc3_readl(dwc, DWC3_DSTS);
\t\tif (!(reg & DWC3_DSTS_DEVCTRLHLT) ||
\t\t    (dwc3_readl(dwc, DWC3_DCTL) & DWC3_DCTL_RUN_STOP)) {
\t\t\tspin_unlock_irqrestore(&dwc->lock, flags);
\t\t\treturn -EAGAIN;
\t\t}
\t}
\tspin_unlock_irqrestore(&dwc->lock, flags);

'''
 newfn=oldfn.replace(token,gate)
 candidate=text.replace(oldfn,newfn);assert candidate.replace(newfn,oldfn)==text
 (HERE/'gadget.c').write_text(candidate,newline='\n')
 (HERE/'suspend-retry.patch').write_text(''.join(difflib.unified_diff(text.splitlines(True),candidate.splitlines(True),
    fromfile='halt-error-candidate/drivers/usb/dwc3/gadget.c',tofile='retry-candidate/drivers/usb/dwc3/gadget.c')),newline='\n')
 coretext=core.decode();gadget_names=['dwc3_gadget_run_stop','dwc3_gadget_disable_irq','__dwc3_gadget_ep_disable',
     '__dwc3_gadget_stop','dwc3_gadget_soft_disconnect','dwc3_gadget_suspend']
 core_names=['dwc3_enable_susphy','dwc3_suspend_common','dwc3_runtime_checks','dwc3_runtime_suspend','dwc3_pm_suspend']
 funcs={n:function(candidate,n) for n in gadget_names};funcs.update({n:function(coretext,n) for n in core_names})
 special=coretext[coretext.index('/* Stack-only ownership of SUSPHY'):coretext.index('static int dwc3_suspend_common')]
 extracted='\n\n'.join(funcs[n] for n in gadget_names+[core_names[0]])+'\n\n'+special+'\n\n'
 extracted+='\n\n'.join(funcs[n] for n in core_names[1:])+'\n'
 (HERE/'tested-functions.inc').write_text(extracted,newline='\n')
 previous=oldfn.replace('dwc3_gadget_suspend(','previous_gadget_suspend(',1)+'\n\n'
 previous+=funcs['dwc3_suspend_common'].replace('dwc3_suspend_common(','previous_suspend_common(',1).replace('dwc3_gadget_suspend(','previous_gadget_suspend(')+'\n'
 (HERE/'previous-functions.inc').write_text(previous,newline='\n')
 result=dict(passed=True,inputs={'gadget.c':sha(original),'core.c':sha(core),'core.h':sha(header)},
  candidate_gadget_sha256=sha(candidate.encode()),changed_existing_functions=['dwc3_gadget_suspend'],
  prior_first_failure_and_true_intent_policy_byte_unchanged=True,core_and_header_unchanged=True,
  actual_function_sha256={n:sha(v.encode()) for n,v in funcs.items()},
  gate_mmio='DSTS.DEVCTRLHLT set and DCTL.RUN_STOP clear, only active software-no-pullup entry',
  no_repeated_request_teardown_reset_or_new_poll=True,
  snapshot_is_not_run_stop_writer_or_full_PM_lifetime_serialization=True,
  full_resume_unwind_complete=False)
 (HERE/'source-result.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(dict(prepared=True,gadget_sha256=result['candidate_gadget_sha256'])))


if __name__=='__main__':main()
