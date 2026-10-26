"""Create this leaf's DWC candidate from frozen R2 + fixed Image source."""
from pathlib import Path
import hashlib, json, difflib
HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
R2 = REF/'charging-oem-audit-20261023/apsd-dwc-window-candidate-r2'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
pins = {'core.h':'eadd437fb786868b75f8d806bf00cd6571422dcd0032a9c6d7e7a11f4a6e564c',
        'core.c':'1dc9c1961a0c0b74f42c65c739702e305b9378fcbea9a348d1e73e97fd72b846',
        'gadget.c':'0153f79691ef73473e791341c710d092421213cffbd5fbe07411a00037daa07a'}
base = {n:(R2/n).read_text() for n in pins}
for n,p in pins.items(): assert sha(R2/n) == p
out = dict(base)
def replace(name, old, new):
    assert out[name].count(old) == 1, (name, old[:100])
    out[name] = out[name].replace(old,new)
replace('core.h','#include <linux/power_supply.h>',
        '#include <linux/power_supply.h>\n#include "samurai-apsd-owner.h"')
replace('core.c','void dwc3_core_exit(struct dwc3 *dwc)\n{',
        'void dwc3_core_exit(struct dwc3 *dwc)\n{\n\tdwc3_apsd_owner_core_exit(dwc);')
start = out['core.c'].index('static int dwc3_suspend_common(')
end = out['core.c'].index('static int dwc3_resume_common(',start)
chunk = out['core.c'][start:end]
chunk = chunk.replace('\tret = dwc3_gadget_window_pm_enter(dwc);',
'''\tret = dwc3_apsd_owner_pause(dwc, DWC3_APSD_RUNTIME);
\tif (ret)
\t\treturn ret;
\tret = dwc3_gadget_window_pm_enter(dwc);''',1)
chunk = chunk.replace('\tif (ret)\n\t\treturn ret;\n\n\tif (!pm_runtime_suspended',
'''\tif (ret) {
\t\tdwc3_apsd_owner_resume(dwc, DWC3_APSD_RUNTIME);
\t\treturn ret;
\t}

\tif (!pm_runtime_suspended''',1)
chunk = chunk.replace('\tdwc3_gadget_window_pm_exit(dwc);\n\treturn ret;',
'''\tdwc3_gadget_window_pm_exit(dwc);
\tif (ret)
\t\tdwc3_apsd_owner_resume(dwc, DWC3_APSD_RUNTIME);
\treturn ret;''',1)
out['core.c'] = out['core.c'][:start] + chunk + out['core.c'][end:]
start = out['core.c'].index('static int dwc3_resume_common(')
end = out['core.c'].index('static int dwc3_runtime_checks(',start)
chunk = out['core.c'][start:end]
chunk = chunk.replace('\tret = dwc3_gadget_window_pm_enter(dwc);',
'''\tret = dwc3_apsd_owner_pause(dwc, DWC3_APSD_RUNTIME);
\tif (ret)
\t\treturn ret;
\tret = dwc3_gadget_window_pm_enter(dwc);''',1)
chunk = chunk.replace('\tdwc3_gadget_window_pm_exit(dwc);\n\treturn ret;',
'''\tdwc3_gadget_window_pm_exit(dwc);
\tif (!ret)
\t\tdwc3_apsd_owner_resume(dwc, DWC3_APSD_RUNTIME | DWC3_APSD_CORE);
\treturn ret;''',1)
out['core.c'] = out['core.c'][:start]+chunk+out['core.c'][end:]
replace('core.c','\tdwc->detect_system_blocked = false;\n\tspin_unlock_irqrestore(&dwc->lock, flags);',
'''\tdwc->detect_system_blocked = false;
\tspin_unlock_irqrestore(&dwc->lock, flags);
\tdwc3_apsd_owner_resume(dwc, DWC3_APSD_SYSTEM);''')
start = out['core.c'].index('int dwc3_pm_prepare(')
end = out['core.c'].index('EXPORT_SYMBOL_GPL(dwc3_pm_prepare)',start)
chunk = out['core.c'][start:end]
chunk = chunk.replace('\tspin_lock_irqsave(&dwc->lock, flags);',
'''\tret = dwc3_apsd_owner_pause(dwc, DWC3_APSD_SYSTEM);
\tif (ret)
\t\treturn ret;
\tspin_lock_irqsave(&dwc->lock, flags);''',1)
chunk = chunk.replace('\tif (ret)\n\t\treturn ret;\n\n\t/*',
'''\tif (ret) {
\t\tdwc3_apsd_owner_resume(dwc, DWC3_APSD_SYSTEM);
\t\treturn ret;
\t}

\t/*''',1)
out['core.c'] = out['core.c'][:start]+chunk+out['core.c'][end:]
start = out['gadget.c'].index('static int dwc3_gadget_start(')
end = out['gadget.c'].index('static void __dwc3_gadget_stop(',start)
chunk=out['gadget.c'][start:end].replace('\treturn 0;','\tdwc3_apsd_owner_resume(dwc, DWC3_APSD_UDC | DWC3_APSD_CORE);\n\treturn 0;',1)
out['gadget.c']=out['gadget.c'][:start]+chunk+out['gadget.c'][end:]
start=out['gadget.c'].index('static int dwc3_gadget_stop(')
end=out['gadget.c'].index('static void dwc3_gadget_config_params(',start)
chunk=out['gadget.c'][start:end].replace('\tdwc3_gadget_window_shutdown(dwc);','\tdwc3_apsd_owner_stop_pre(dwc);\n\tdwc3_gadget_window_shutdown(dwc);',1)
chunk=chunk.replace('\tfree_irq(dwc->irq_gadget, dwc->ev_buf);','\tfree_irq(dwc->irq_gadget, dwc->ev_buf);\n\tdwc3_apsd_owner_stop_post(dwc);',1)
out['gadget.c']=out['gadget.c'][:start]+chunk+out['gadget.c'][end:]
start=out['gadget.c'].index('int dwc3_gadget_init(')
end=out['gadget.c'].index('EXPORT_SYMBOL_GPL(dwc3_gadget_init)',start)
chunk=out['gadget.c'][start:end].replace('\treturn 0;','\tdwc3_apsd_owner_bind(dwc);\n\treturn 0;',1)
out['gadget.c']=out['gadget.c'][:start]+chunk+out['gadget.c'][end:]
start=out['gadget.c'].index('void dwc3_gadget_exit(')
end=out['gadget.c'].index('EXPORT_SYMBOL_GPL(dwc3_gadget_exit)',start)
chunk=out['gadget.c'][start:end].replace('\tdwc3_gadget_window_shutdown(dwc);',
'''\tdwc3_apsd_owner_stop_pre(dwc);
\tdwc3_gadget_window_shutdown(dwc);
\tdwc3_apsd_owner_stop_post(dwc);''',1)
chunk=chunk.replace('\tmutex_destroy(&dwc->connect_mutex);','\tdwc3_apsd_owner_unbind(dwc);\n\tmutex_destroy(&dwc->connect_mutex);',1)
out['gadget.c']=out['gadget.c'][:start]+chunk+out['gadget.c'][end:]
(HERE/'Makefile.fragment').write_text('dwc3-$(CONFIG_USB_DWC3_SAMURAI_APSD_OWNER) += samurai-apsd-owner.o\n')
(HERE/'Kconfig.fragment').write_text('''
config USB_DWC3_SAMURAI_APSD_OWNER
\tbool "Samurai APSD DWC lifecycle candidate (no attempt gate yet)"
\tdepends on USB_DWC3=y && USB_DWC3_GADGET
\tdepends on SERIAL_EUD_CONSOLE=y && PHY_QCOM_USB_SNPS_FEMTO_V2=y
\tdepends on POWER_SUPPLY=y
\tdefault n
\thelp
\t  Internal optional coordinator, additionally requiring the explicit
\t  samurai,apsd-owner property. Missing PD/route and EUD/PHY lifetime
\t  coverage refuses every hardware attempt. Not a deployable rerun path.
''')
patch=[]
for n,t in out.items():
    (HERE/n).write_text(t)
    patch.extend(difflib.unified_diff(base[n].splitlines(True), t.splitlines(True),
                 'a/drivers/usb/dwc3/'+n,'b/drivers/usb/dwc3/'+n))
(HERE/'dwc-lifecycle.patch').write_text(''.join(patch))
(HERE/'source-inputs.json').write_text(json.dumps({'frozen_r2':pins,
    'candidate':{n:sha(HERE/n) for n in out}},indent=2)+'\n')
print('Prepared three private DWC files and two build fragments; frozen inputs unchanged.')
