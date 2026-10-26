"""Derive only the native PSY software-budget fence from exact fixed sources."""
from pathlib import Path
import difflib,hashlib,json,re
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'apsd-integration/current-r7/snapshots'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
PINS={'core.c':'bd8a8aabf199952717926b8ee79562e283ed9cd6a1ee485d22cd52167ad7ffcf',
      'core.h':'525c1d5d8d0e501f4a92ddd6232961542b5c04521f29a50b8acf9ee86c41373c',
      'gadget.c':'9eec86e42945a786447e6a6548a25b495e29a01bed8e8fbfc13e02903e1ff0c5'}
def function(text,name):
    m=re.search(r'(?m)^(?:static )?(?:[\w*]+[ \t]+)+\b'+re.escape(name)+r'\s*\(',text)
    assert m,name
    start=m.start();i=text.index('{',m.end())+1;depth=1
    while depth:
        depth+=(text[i]=='{')-(text[i]=='}');i+=1
    return text[start:i]+'\n'
def swap(text,name,old,new):
    assert old!=new and text.count(old)==1,name
    return text.replace(old,new,1)
def main():
    raws={n:(BASE/('drivers--usb--dwc3--'+n)).read_bytes() for n in PINS}
    for n,pin in PINS.items():assert sha(raws[n])==pin,n
    old={n:raw.decode() for n,raw in raws.items()};new=dict(old)
    core=old['core.c'];changed={}
    name='dwc3_vbus_draw_work';before=function(core,name)
    work=(HERE/'budget-work.c.inc').read_text()
    core=swap(core,name,before,work);changed[name]=before
    name='dwc3_psy_notifier';before=function(core,name)
    after=before.replace('if (dwc->current_limit != DWC3_CURRENT_UNSPECIFIED)',
        'if (!dwc->vbus_draw_blocked &&\n\t    dwc->current_limit != DWC3_CURRENT_UNSPECIFIED)')
    core=swap(core,name,before,after);changed[name]=before
    name='dwc3_get_usb_power_supply';before=function(core,name)
    after=before.replace('\tdwc->current_limit = DWC3_CURRENT_UNSPECIFIED;\n',
        '\tdwc->current_limit = DWC3_CURRENT_UNSPECIFIED;\n\tdwc->vbus_draw_blocked = false;\n')
    core=swap(core,name,before,after);changed[name]=before
    name='dwc3_pm_suspend';before=function(core,name)
    after=before.replace('\tpinctrl_pm_select_sleep_state(dev);',
        '\tdwc3_vbus_budget_close(dwc);\n\tpinctrl_pm_select_sleep_state(dev);')
    core=swap(core,name,before,after);changed[name]=before
    name='dwc3_pm_resume';before=function(core,name)
    after=before.replace('\tret = dwc3_resume_common(dwc, PMSG_RESUME);',
        '\tdwc3_vbus_budget_open(dwc);\n\tret = dwc3_resume_common(dwc, PMSG_RESUME);')
    after=after.replace('out:\n\tpm_runtime_enable(dev);',
        'out:\n\tif (ret)\n\t\tdwc3_vbus_budget_close(dwc);\n\tpm_runtime_enable(dev);')
    core=swap(core,name,before,after);changed[name]=before
    new['core.c']=core
    header=old['core.h'].replace(' * @current_limit: How much current to draw from vbus, in milliAmperes.\n',
        ' * @current_limit: How much current to draw from vbus, in milliAmperes.\n * @vbus_draw_blocked: System-PM software allowance publication gate.\n')
    header=header.replace('\tunsigned int\t\tcurrent_limit;\n',
        '\tunsigned int\t\tcurrent_limit;\n\tbool\t\t\tvbus_draw_blocked;\n')
    assert header!=old['core.h'];new['core.h']=header
    before=function(old['gadget.c'],'dwc3_gadget_vbus_draw')
    after=before.replace('\tspin_lock_irqsave(&dwc->lock, flags);\n',
        '\tspin_lock_irqsave(&dwc->lock, flags);\n\tif (dwc->vbus_draw_blocked) {\n\t\tspin_unlock_irqrestore(&dwc->lock, flags);\n\t\treturn -EBUSY;\n\t}\n',1)
    new['gadget.c']=swap(old['gadget.c'],'dwc3_gadget_vbus_draw',before,after)
    patches=[]
    for n in PINS:
        (HERE/n).write_text(new[n],encoding='utf-8',newline='\n')
        patches.extend(difflib.unified_diff(old[n].splitlines(True),new[n].splitlines(True),
            fromfile='Image363/drivers/usb/dwc3/'+n,tofile='budget-fence/drivers/usb/dwc3/'+n))
    (HERE/'budget-fence.patch').write_text(''.join(patches),encoding='utf-8',newline='\n')
    restored=core
    for n,before in changed.items():
        if n=='dwc3_vbus_draw_work':restored=restored.replace(work,before,1)
        else:restored=restored.replace(function(core,n),before,1)
    assert restored==old['core.c']
    assert new['gadget.c'].replace(function(new['gadget.c'],'dwc3_gadget_vbus_draw'),
        function(old['gadget.c'],'dwc3_gadget_vbus_draw'),1)==old['gadget.c']
    unchanged=['dwc3_suspend_common','dwc3_resume_common','dwc3_runtime_suspend',
        'dwc3_runtime_resume','dwc3_runtime_idle','dwc3_pm_prepare','dwc3_pm_complete','dwc3_core_remove']
    for n in unchanged:assert function(core,n)==function(old['core.c'],n),n
    names=['dwc3_vbus_draw_work','dwc3_vbus_budget_close','dwc3_vbus_budget_open',
        'dwc3_psy_notifier','dwc3_get_usb_power_supply','dwc3_pm_suspend','dwc3_pm_resume']
    (HERE/'actual-budget-core.inc').write_text('\n'.join(function(core,n) for n in names),encoding='utf-8',newline='\n')
    (HERE/'actual-budget-gadget.inc').write_text(function(new['gadget.c'],'dwc3_gadget_vbus_draw'),encoding='utf-8',newline='\n')
    (HERE/'actual-old-worker.inc').write_text(function(old['core.c'],'dwc3_vbus_draw_work').replace(
        'dwc3_vbus_draw_work','old_dwc3_vbus_draw_work',1),encoding='utf-8',newline='\n')
    (HERE/'actual-old-pm.inc').write_text('\n'.join(function(old['core.c'],n).replace(
        n,'old_'+n,1) for n in ['dwc3_pm_suspend','dwc3_pm_resume']),encoding='utf-8',newline='\n')
    provider=HERE.parent/'usb-input-flat-consumer-candidate/samurai-usb-input.c'
    assert sha(provider.read_bytes())=='ee0f0806c5a51576f10b299aca173c61ab2b4764a5954c1039d1c73327878a88'
    (HERE/'actual-provider.inc').write_text('\n'.join(function(provider.read_text(),n) for n in
        ['samurai_usb_set_property','samurai_usb_stop','samurai_usb_suspend','samurai_usb_resume']),encoding='utf-8',newline='\n')
    result=dict(passed=True,baseline={n:dict(path=str(BASE/('drivers--usb--dwc3--'+n)),sha256=p) for n,p in PINS.items()},
        candidate={n:sha((HERE/n).read_bytes()) for n in PINS},
        all_other_core_and_gadget_bytes_identical=True,old_core_functions_byte_identical=unchanged,
        changed_core_functions=list(changed),changed_gadget_function='dwc3_gadget_vbus_draw',
        direct_complete_or_runtime_PM_changed=False,old_PHY_vbus_path_changed=False,
        gadget_closed_gate_errno='-EBUSY; no storage, queue or later replay',
        provider_fixture_source_sha256=sha(provider.read_bytes()),
        extracts={n:sha((HERE/n).read_bytes()) for n in ['actual-budget-core.inc','actual-budget-gadget.inc','actual-old-worker.inc','actual-old-pm.inc','actual-provider.inc']},
        device_SDK_build_or_shared_source_accessed=False)
    (HERE/'source-result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(result))
if __name__=='__main__':main()
