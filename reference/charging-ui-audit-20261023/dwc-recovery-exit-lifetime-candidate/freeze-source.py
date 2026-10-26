"""Bind exact changed sources, original caller contract and eight new cases."""
from pathlib import Path
import hashlib
import json
import re
import sys
sys.dont_write_bytecode = True
HERE=Path(__file__).resolve().parent
REF=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def function(text,name):
    m=re.search(r'^(?:static\s+)?(?:inline\s+)?(?:int|void|bool|irqreturn_t)\s+'
                +name+r'\([^;]*?\)\s*\{',text,re.M)
    if m is None:raise ValueError(name)
    pos=text.index('{',m.start())+1;end=pos;depth=1
    while depth:
        depth+=(text[end]=='{')-(text[end]=='}');end+=1
    return text[m.start():end]


def apply_diff(patch,original):
    # Only the generated two-file unified patch, in RAM. Strict context/counts.
    result={};rows=patch.splitlines(True);i=0
    while i<len(rows):
        if not rows[i].startswith('--- a/'):raise ValueError('old file header')
        name=rows[i][6:].rstrip('\n');i+=1
        if rows[i]!='+++ b/'+name+'\n':raise ValueError('new file header')
        i+=1;src=original[name].splitlines(True);out=[];at=0
        while i<len(rows) and not rows[i].startswith('--- a/'):
            m=re.fullmatch(r'@@ -(\d+),(\d+) \+(\d+),(\d+) @@\n',rows[i])
            if not m:raise ValueError('hunk header')
            old_start,old_count,new_start,new_count=map(int,m.groups());i+=1
            if old_start-1<at:raise ValueError('overlap')
            out+=src[at:old_start-1];at=old_start-1
            if len(out)!=new_start-1:raise ValueError('new position')
            consumed=produced=0
            while i<len(rows) and not rows[i].startswith(('@@ ','--- a/')):
                r=rows[i];i+=1
                if r[0] in ' -':
                    if at>=len(src) or src[at]!=r[1:]:raise ValueError('context')
                    at+=1;consumed+=1
                if r[0] in ' +':out.append(r[1:]);produced+=1
                if r[0] not in ' +-':raise ValueError('body')
            if (consumed,produced)!=(old_count,new_count):raise ValueError('hunk counts')
        out+=src[at:];result[name]=''.join(out)
    return result


def main():
    if sys.flags.optimize:raise RuntimeError('Nonoptimized interpreter required')
    tests=json.loads((HERE/'test-result.json').read_bytes())
    if not tests['passed'] or tests['summary']['cases']!=8:raise ValueError('tests')
    for n,h in tests['files'].items():
        if sha(HERE/n)!=h:raise ValueError(n)
    BASE=REF/'charging-session-20261023/dwc-device-resume-outcome-candidate'
    original={'drivers/usb/dwc3/'+n:(BASE/n).read_text() for n in ['gadget.c','core.h']}
    applied=apply_diff((HERE/'recovery-exit-lifetime.patch').read_text(),original)
    if applied!={'drivers/usb/dwc3/'+n:(HERE/n).read_text() for n in ['gadget.c','core.h']}:
        raise ValueError('Patch output')
    udc=REF/'charging-oem-audit-20261023/usb-resume-errors/drivers--usb--gadget--udc--core.c'
    manifest=udc.parent/'source-manifest.json'
    if sha(udc)!='17d0d78f3de3d3dbf28d7136496a1a92c5e3744791b3221269b58c0aecd91041':
        raise ValueError('UDC snapshot')
    if json.loads(manifest.read_bytes())['drivers/usb/gadget/udc/core.c']['sha256']!=sha(udc):
        raise ValueError('UDC manifest')
    devicecore=REF/'charging-oem-audit-20261023/usb-input-irq-candidate/source-reference/drivers--base--core.c'
    core=REF/'charging-ui-audit-20261023/dwc-pm-error-unwind-candidate/core.c'
    g=HERE/'gadget.c'
    inputs={udc:['usb_del_gadget','gadget_unbind_driver','usb_gadget_udc_stop_locked',
                 'usb_gadget_disconnect_locked'],
            devicecore:['device_del'],
            core:['__dwc3_set_mode','dwc3_core_remove','dwc3_runtime_resume','dwc3_pm_resume'],
            g:['dwc3_gadget_pullup','dwc3_gadget_stop','dwc3_gadget_exit',
               'dwc3_gadget_ep_disable','dwc3_gadget_ep_dequeue','dwc3_check_event_buf']}
    evidence={}
    for p,names in inputs.items():
        text=p.read_text();fs={}
        for name in names:
            body=function(text,name)
            fs[name]=dict(line=text[:text.index(body)].count('\n')+1,
                          sha256=hashlib.sha256(body.encode()).hexdigest())
        evidence[p.relative_to(REF).as_posix()]=dict(sha256=sha(p),bytes=p.stat().st_size,functions=fs)
    t=udc.read_text()
    if '.remove = gadget_unbind_driver,' not in t:raise ValueError('bus remove')
    entry=t.index('static const struct bus_type gadget_bus_type = {')
    proof=dict(passed=True,sources=evidence,udc_original_manifest_sha256=sha(manifest),
        gadget_bus_remove_line=t[:entry].count('\n')+1,
        synchronous_unbind_basis='usb_del_gadget documented contract + device_del/bus remove API; actual UDC remove/start-stop functions pinned',
        generic_bus_dd_newly_imported=False,
        source_core_not_changed=True,patch_applied_in_RAM_matches_both_complete_files=True,
        complete_PM_abort_or_DMA_lifetime_proved=False)
    (HERE/'caller-source-evidence.json').write_text(json.dumps(proof,indent=2)+'\n')
    names=['README.md','prepare.py','freeze-source.py','gadget.c','core.h',
           'recovery-exit-lifetime.patch','source-result.json','caller-source-evidence.json',
           'actual-functions.inc','previous-functions.inc','test-lifetime.c',
           'test-lifetime.py','test-result.json']
    result=dict(schema=1,passed=True,frozen=True,scope='exit-only recovery-work lifetime; no PM consumer',
        files={n:dict(sha256=sha(HERE/n),bytes=(HERE/n).stat().st_size) for n in names},
        new_cases=8,old_suites_rerun=False,single_object_build_not_yet_executed=True,
        struct_layout_changed_requires_consistent_future_rebuild=True,
        full_resume_abort_complete=False,device_SSH_USB_SDK_Image_Git_used=False)
    (HERE/'source-delivery.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(passed=True,delivery_sha256=sha(HERE/'source-delivery.json'),
                         caller_evidence_sha256=sha(HERE/'caller-source-evidence.json'))))


if __name__=='__main__':main()
