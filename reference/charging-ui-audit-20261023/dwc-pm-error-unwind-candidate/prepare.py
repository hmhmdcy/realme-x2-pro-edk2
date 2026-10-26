"""Derive one SUSPHY-on-failed-suspend fix from the exact Image503 core."""
from pathlib import Path
import difflib
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
CORE = REF / 'charging-oem-audit-20261023/usb-resume-errors/drivers--usb--dwc3--core.c'
GADGET = REF / 'charging-session-20261023/dwc-device-start-recovery-candidate/gadget.c'
HEADER = GADGET.with_name('core.h')
sha = lambda raw: hashlib.sha256(raw).hexdigest()

def function(source, name):
    match = re.search(r'^(?:(?:static|inline)\s+)*(?:int|void|bool)\s+' + name + r'\([^;]*?\)\s*\{', source, re.M)
    if match is None: raise RuntimeError('missing function ' + name)
    at = source.index('{', match.start()); end = at + 1; depth = 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}'); end += 1
    return source[match.start():end]

helper = '''/* Stack-only ownership of SUSPHY bits changed by this suspend attempt.
 * No IRQ, core, PHY or PM lifetime is owned by this record.
 */
struct dwc3_suspend_susphy {
	u32 usb2_saved, usb3_saved;
	u32 usb2_changed, usb3_changed;
};

static void dwc3_suspend_susphy_enable(struct dwc3 *dwc,
				       struct dwc3_suspend_susphy *saved)
{
	u32 reg, next;
	int i;

	/* Match dwc3_enable_susphy(true), recording the actual same-read delta.
	 * In particular, an enable request can clear a bit under a quirk.
	 */
	for (i = 0; i < dwc->num_usb3_ports; i++) {
		reg = dwc3_readl(dwc, DWC3_GUSB3PIPECTL(i));
		if (reg & DWC3_GUSB3PIPECTL_SUSPHY)
			saved->usb3_saved |= BIT(i);
		next = dwc->dis_u3_susphy_quirk ?
			reg & ~DWC3_GUSB3PIPECTL_SUSPHY : reg | DWC3_GUSB3PIPECTL_SUSPHY;
		if (next != reg)
			saved->usb3_changed |= BIT(i);
		dwc3_writel(dwc, DWC3_GUSB3PIPECTL(i), next);
	}
	for (i = 0; i < dwc->num_usb2_ports; i++) {
		reg = dwc3_readl(dwc, DWC3_GUSB2PHYCFG(i));
		if (reg & DWC3_GUSB2PHYCFG_SUSPHY)
			saved->usb2_saved |= BIT(i);
		next = dwc->dis_u2_susphy_quirk ?
			reg & ~DWC3_GUSB2PHYCFG_SUSPHY : reg | DWC3_GUSB2PHYCFG_SUSPHY;
		if (next != reg)
			saved->usb2_changed |= BIT(i);
		dwc3_writel(dwc, DWC3_GUSB2PHYCFG(i), next);
	}
}

static void dwc3_suspend_susphy_restore(struct dwc3 *dwc,
					struct dwc3_suspend_susphy *saved)
{
	u32 reg, next;
	int i;

	/* The callback failed before core_exit. Keep all resources ACTIVE and
	 * undo only this attempt's changed bits, preserving other current bits.
	 */
	for (i = 0; i < dwc->num_usb3_ports; i++) {
		if (!(saved->usb3_changed & BIT(i)))
			continue;
		reg = dwc3_readl(dwc, DWC3_GUSB3PIPECTL(i));
		next = (reg & ~DWC3_GUSB3PIPECTL_SUSPHY) |
			(saved->usb3_saved & BIT(i) ? DWC3_GUSB3PIPECTL_SUSPHY : 0);
		if (next != reg)
			dwc3_writel(dwc, DWC3_GUSB3PIPECTL(i), next);
	}
	for (i = 0; i < dwc->num_usb2_ports; i++) {
		if (!(saved->usb2_changed & BIT(i)))
			continue;
		reg = dwc3_readl(dwc, DWC3_GUSB2PHYCFG(i));
		next = (reg & ~DWC3_GUSB2PHYCFG_SUSPHY) |
			(saved->usb2_saved & BIT(i) ? DWC3_GUSB2PHYCFG_SUSPHY : 0);
		if (next != reg)
			dwc3_writel(dwc, DWC3_GUSB2PHYCFG(i), next);
	}
}

'''

if __name__ == '__main__':
    original = CORE.read_text()
    if sha(CORE.read_bytes()) != 'bd8a8aabf199952717926b8ee79562e283ed9cd6a1ee485d22cd52167ad7ffcf': raise RuntimeError('exact core input')
    if sha(GADGET.read_bytes()) != 'ca4bf1c5a1afa42267d2f7f8b636dfe7ca5a1b9581307093f93a892e2f004314': raise RuntimeError('exact #503 gadget')
    if sha(HEADER.read_bytes()) != '9a8dc48a1283db17b6a0cad01f0bc43ff916cfa7dc3a11b680c2145984f97a67': raise RuntimeError('exact #503 header')
    old = function(original, 'dwc3_suspend_common')
    new = old.replace('{\n\tu32 reg;', '{\n\tstruct dwc3_suspend_susphy saved_susphy = { 0 };\n\tu32 reg;', 1)
    new = new.replace('(dwc3_readl(dwc, DWC3_GUSB2PHYCFG(0)) &', '(dwc->num_usb2_ports && (dwc3_readl(dwc, DWC3_GUSB2PHYCFG(0)) &', 1)
    new = new.replace('DWC3_GUSB2PHYCFG_SUSPHY) ||', 'DWC3_GUSB2PHYCFG_SUSPHY)) ||', 1)
    new = new.replace('(dwc3_readl(dwc, DWC3_GUSB3PIPECTL(0)) &', '(dwc->num_usb3_ports && (dwc3_readl(dwc, DWC3_GUSB3PIPECTL(0)) &', 1)
    new = new.replace('DWC3_GUSB3PIPECTL_SUSPHY);', 'DWC3_GUSB3PIPECTL_SUSPHY));', 1)
    new = new.replace('if (!dwc->susphy_state)\n\t\t\tdwc3_enable_susphy(dwc, true);', '''if (!dwc->susphy_state) {
			if (dwc->current_dr_role == DWC3_GCTL_PRTCAP_DEVICE ||
			    (dwc->current_dr_role == DWC3_GCTL_PRTCAP_OTG &&
			     dwc->current_otg_role == DWC3_OTG_ROLE_DEVICE))
				dwc3_suspend_susphy_enable(dwc, &saved_susphy);
			else
				dwc3_enable_susphy(dwc, true);
		}''', 1)
    new, count = re.subn(r'if \(ret\)\n(\s*)return ret;', r'if (ret)\n\1goto restore_susphy;', new)
    if count != 2: raise RuntimeError('only two gadget suspend errors')
    new = new[:-1] + '''restore_susphy:
	dwc3_suspend_susphy_restore(dwc, &saved_susphy);
	return ret;
}'''
    candidate = original.replace(old, helper + new, 1)
    (HERE / 'core.c').write_text(candidate)
    (HERE / 'suspend-susphy.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True), candidate.splitlines(True), fromfile='Image503/drivers/usb/dwc3/core.c', tofile='candidate/drivers/usb/dwc3/core.c')))
    names = ['dwc3_enable_susphy', 'dwc3_suspend_susphy_enable', 'dwc3_suspend_susphy_restore', 'dwc3_suspend_common',
             'dwc3_runtime_checks', 'dwc3_runtime_suspend', 'dwc3_pm_suspend']
    declaration = helper[:helper.index('static void')]
    actual = declaration + '\n'.join(function(candidate, name) for name in names) + '\n' + function(GADGET.read_text(), 'dwc3_gadget_suspend') + '\n'
    (HERE / 'tested-functions.inc').write_text(actual)
    (HERE / 'original-suspend.inc').write_text(old.replace('dwc3_suspend_common(', 'original_suspend_common(', 1) + '\n')
    evidence = {'source_commit': 'ba61a62293e0f6bc5838c06f2e85e033e3d702a8',
                'original_core_sha256': sha(CORE.read_bytes()), 'Image503_gadget_sha256': sha(GADGET.read_bytes()),
                'Image503_core_h_sha256': sha(HEADER.read_bytes()), 'candidate_core_sha256': sha((HERE / 'core.c').read_bytes()),
                'changed_existing_functions': ['dwc3_suspend_common'], 'new_helpers_are_static_stack_only': True,
                'actual_test_functions': {name: sha(function(candidate, name).encode()) for name in names},
                'actual_gadget_suspend_sha256': sha(function(GADGET.read_text(), 'dwc3_gadget_suspend').encode()),
                'resume_common_and_callers_byte_exact': all(function(candidate, name) == function(original, name) for name in
                    ['dwc3_resume_common', 'dwc3_runtime_resume', 'dwc3_pm_resume', 'dwc3_core_exit', 'dwc3_event_buffers_cleanup']),
                'full_resume_error_unwind_complete': False}
    (HERE / 'source-result.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(json.dumps({'prepared': True, 'candidate_core_sha256': evidence['candidate_core_sha256']}))
