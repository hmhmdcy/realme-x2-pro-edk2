from pathlib import Path
import hashlib,importlib.util,json,re,sys
HERE=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
# Import only the source extractor definition, not prepare.py's generator.
source=(HERE/'prepare.py').read_text()
namespace={'re':re};exec(source[source.index('def extract('):source.index('original=paths')],namespace)
extract=namespace['extract'];gadget=(HERE/'gadget.c').read_text()
record=json.loads((HERE/'source-result.json').read_text())
core_path=HERE.parent/'apsd-integration/current-r7/snapshots/drivers--usb--dwc3--core.c';core=core_path.read_text()
sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(core_path.read_bytes())==record['original']['core.c']['sha256']
names=['dwc3_schedule_err_recovery','dwc3_gadget_soft_connect','dwc3_gadget_recover_locked',
 'dwc3_err_recovery_work','dwc3_gadget_resume','dwc3_resume_common','dwc3_runtime_resume','dwc3_pm_resume']
functions=[extract(core if n in names[-3:] else gadget,n) for n in names]
struct=re.search(r'^struct dwc3_recovery_result \{.*?^\};',gadget,re.M|re.S).group()
(HERE/'tested-functions.inc').write_text(struct+'\n\n'+'\n\n'.join(functions)+'\n')
manifest=[dict(name=n,source='core.c(original)' if n in names[-3:] else 'gadget.c(candidate)',
 line=(core if n in names[-3:] else gadget)[:(core if n in names[-3:] else gadget).index(f)].count('\n')+1,
 sha256=sha(f.encode())) for n,f in zip(names,functions)]
(HERE/'function-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
base=(HERE/'baseline-gadget.c').read_text()
for name in ['dwc3_gadget_suspend','dwc3_gadget_run_stop','dwc3_gadget_soft_disconnect','dwc3_gadget_pullup','dwc3_gadget_reset_interrupt','dwc3_gadget_exit','dwc3_gadget_start','dwc3_gadget_stop']:
 assert extract(gadget,name)==extract(base,name),name
assert 'pm_runtime_' not in extract(gadget,'dwc3_gadget_recover_locked')
assert 'disable_irq' not in extract(gadget,'dwc3_gadget_recover_locked')
assert 'enable_irq' not in extract(gadget,'dwc3_gadget_recover_locked')
assert 'while (' not in extract(gadget,'dwc3_gadget_recover_locked')
assert 'for (' not in extract(gadget,'dwc3_gadget_recover_locked')
assert (HERE/'core.h').read_text().count('u64\t\t\terr_event_seq;')==1
