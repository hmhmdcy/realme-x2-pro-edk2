"""Independent DEVICE-only cleanup revision; root/R2 artifacts stay frozen."""
from pathlib import Path
import difflib
import hashlib
import json

HERE = Path(__file__).resolve().parent
AUDIT = HERE.parents[1] / 'charging-oem-audit-20261023'
FIRST = AUDIT / 'apsd-dwc-resume-error-candidate'
R2 = AUDIT / 'apsd-dwc-window-candidate-r2'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(FIRST / 'core.c') == 'cdff700a415cfa0de231dded3b00b18a31aae23de19dd4a894c894517bc06e2d'
assert sha(R2 / 'gadget.c') == '0153f79691ef73473e791341c710d092421213cffbd5fbe07411a00037daa07a'
assert sha(R2 / 'core.h') == 'eadd437fb786868b75f8d806bf00cd6571422dcd0032a9c6d7e7a11f4a6e564c'
core = original_core = (FIRST / 'core.c').read_text()
gadget = original_gadget = (R2 / 'gadget.c').read_text()
header = original_header = (R2 / 'core.h').read_text()


def once(text, old, new):
    assert text.count(old) == 1, old[:90]
    return text.replace(old, new)


core = once(core, 'void dwc3_core_exit(struct dwc3 *dwc)\n{\n',
'''void dwc3_core_exit(struct dwc3 *dwc)
{
	/* Failed-resume rollback already balanced the core lifecycle. */
	if (READ_ONCE(dwc->resume_core_exited))
		return;
''')
device = '''	case DWC3_GCTL_PRTCAP_DEVICE:
		ret = dwc3_core_init_for_resume(dwc);'''
core = once(core, device, '''	case DWC3_GCTL_PRTCAP_DEVICE:
		if (READ_ONCE(dwc->resume_failed)) {
			ret = -ESHUTDOWN;
			goto out;
		}
		ret = dwc3_core_init_for_resume(dwc);''')
core = once(core, '''		ret = dwc3_gadget_resume(dwc);
		if (ret)
			goto out;
		break;''', '''		ret = dwc3_gadget_resume(dwc);
		if (ret) {
			int cleanup_error = dwc3_gadget_abort_resume(dwc);

			if (cleanup_error)
				dev_err(dwc->dev, "gadget resume abort failed: %d (resume %d)\\n",
					cleanup_error, ret);
			dwc3_core_exit(dwc);
			WRITE_ONCE(dwc->resume_core_exited, true);
			goto out;
		}
		break;''')
core = once(core, '''			ret = dwc3_gadget_resume(dwc);
			if (ret)
				goto out;''', '\t\t\tdwc3_gadget_resume(dwc);')
header = once(header, '\tenum dwc3_err_state\terr_state;\n', '''	enum dwc3_err_state	err_state;
	/* Terminal failed-DEVICE-resume bookkeeping, reset only by new core. */
	bool			resume_failed;
	/* core_exit ran; not proof that hardware power-off succeeded. */
	bool			resume_core_exited;
	/* One Linux IRQ disable owned by abort, released after free_irq. */
	bool			resume_irq_parked;
''')
header = once(header, 'int dwc3_gadget_resume(struct dwc3 *dwc);',
              'int dwc3_gadget_resume(struct dwc3 *dwc);\nint dwc3_gadget_abort_resume(struct dwc3 *dwc);')
header = once(header, '''static inline int dwc3_gadget_resume(struct dwc3 *dwc)
{
	return 0;
}''', '''static inline int dwc3_gadget_resume(struct dwc3 *dwc)
{
	return 0;
}

static inline int dwc3_gadget_abort_resume(struct dwc3 *dwc)
{
	return 0;
}''')
gadget = once(gadget, '''	irq = dwc->irq_gadget;
	ret = request_threaded_irq''', '''	mutex_lock(&dwc->connect_mutex);
	if (READ_ONCE(dwc->resume_failed)) {
		mutex_unlock(&dwc->connect_mutex);
		return -ESHUTDOWN;
	}
	irq = dwc->irq_gadget;
	ret = request_threaded_irq''')
gadget = once(gadget, '''		dev_err(dwc->dev, "failed to request irq #%d --> %d\\n",
				irq, ret);
		return ret;''', '''		dev_err(dwc->dev, "failed to request irq #%d --> %d\\n",
				irq, ret);
		mutex_unlock(&dwc->connect_mutex);
		return ret;''')
gadget = once(gadget, '''	dwc->gadget_driver	= driver;
	spin_unlock_irqrestore(&dwc->lock, flags);''', '''	dwc->gadget_driver	= driver;
	spin_unlock_irqrestore(&dwc->lock, flags);
	mutex_unlock(&dwc->connect_mutex);''')
gadget = once(gadget, '''	spin_lock_irqsave(&dwc->lock, flags);
	dwc->gadget_driver	= NULL;''', '''	mutex_lock(&dwc->connect_mutex);
	spin_lock_irqsave(&dwc->lock, flags);
	dwc->gadget_driver	= NULL;''')
gadget = once(gadget, '''	free_irq(dwc->irq_gadget, dwc->ev_buf);

	return 0;''', '''	free_irq(dwc->irq_gadget, dwc->ev_buf);
	if (dwc->resume_irq_parked) {
		dwc->resume_irq_parked = false;
		enable_irq(dwc->irq_gadget);
	}
	mutex_unlock(&dwc->connect_mutex);

	return 0;''')
gadget = once(gadget, '''	dwc->softconnect = is_on;
	if (dwc3_gadget_window_busy(dwc))''', '''	dwc->softconnect = is_on;
	if (dwc->resume_failed) {
		spin_unlock_irqrestore(&dwc->lock, flags);
		return is_on ? -ESHUTDOWN : 0;
	}
	if (dwc3_gadget_window_busy(dwc))''')
gadget = once(gadget, 'if (!READ_ONCE(dwc->detect_stopping)) {',
              'if (!READ_ONCE(dwc->detect_stopping) && !READ_ONCE(dwc->resume_failed)) {')
gadget = once(gadget, '''	dwc3_gadget_window_shutdown(dwc);
	dwc3_enable_susphy(dwc, true);''', '''	dwc3_gadget_window_shutdown(dwc);
	if (!READ_ONCE(dwc->resume_core_exited))
		dwc3_enable_susphy(dwc, true);''')
gadget = once(gadget, '''int dwc3_gadget_suspend(struct dwc3 *dwc)
{
	int ret;
''', '''int dwc3_gadget_suspend(struct dwc3 *dwc)
{
	int ret;

	if (READ_ONCE(dwc->resume_core_exited))
		return 0;
''')
gadget = once(gadget, 'int dwc3_gadget_resume(struct dwc3 *dwc)\n{\n',
              (HERE / 'abort-resume.inc').read_text() + '''

int dwc3_gadget_resume(struct dwc3 *dwc)
{
	if (READ_ONCE(dwc->resume_failed))
		return -ESHUTDOWN;
''')
texts = {'core.c': core, 'gadget.c': gadget, 'core.h': header}
originals = {'core.c': original_core, 'gadget.c': original_gadget, 'core.h': original_header}
patch = ''
for name, text in texts.items():
    (HERE / name).write_bytes(text.encode())
    patch += ''.join(difflib.unified_diff(originals[name].splitlines(True), text.splitlines(True),
                    fromfile='a/drivers/usb/dwc3/' + name, tofile='b/drivers/usb/dwc3/' + name))
(HERE / 'device-cleanup.patch').write_bytes(patch.encode())
result = {'baseline': 'root resume candidate core + frozen R2 gadget/header',
          'files': {n: sha(HERE / n) for n in texts}, 'patch_sha256': sha(HERE / 'device-cleanup.patch'),
          'otg_negative_return_change_reverted': True, 'host_unchanged': True,
          'automatic_reconnect_added': False, 'root_r2_or_first_candidate_modified': False}
(HERE / 'source-result.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
print(json.dumps(result, indent=2))
