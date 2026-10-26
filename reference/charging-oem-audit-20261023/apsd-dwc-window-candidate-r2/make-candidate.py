"""Generate a private three-file DWC3 patch from pinned original Image bytes."""
from pathlib import Path
import difflib
import hashlib
import json

HERE=Path(__file__).resolve().parent


def replace(text,old,new):
 assert text.count(old)==1,old[:90]
 return text.replace(old,new,1)


def function(text,name):
 import re
 m=re.search(r'^(?:static\s+)?[\w\s*]+?\b'+name+r'\([^;]*?\)\n\{',text,re.M);assert m,name
 a=m.start()
 while text[a]=='\n':a+=1
 b=text.index('\n}',m.end())+2
 return text[a:b]


def main():
 h=(HERE/'baseline/core.h').read_text()
 types='''enum dwc3_gadget_window_state {
	DWC3_WINDOW_IDLE,
	DWC3_WINDOW_CLAIMED,
	DWC3_WINDOW_HALTED,
	DWC3_WINDOW_RESTORING,
	DWC3_WINDOW_FAILED,
	DWC3_WINDOW_SHUTDOWN,
};

/* DWC3-internal state, not UAPI or an exported kernel/module ABI. */
struct dwc3_gadget_window {
	u64 cookie;
	enum dwc3_gadget_window_state state;
	bool pm_ref;
	bool halted;
	bool cancelled;
	bool recovery_pending;
	int halt_error;
	int restore_error;
};

struct dwc3_gadget_window_result {
	u64 cookie;
	enum dwc3_gadget_window_state state;
	bool halted;
	bool cancelled;
	bool restore_wanted;
	int halt_error;
	int restore_error;
};

'''
 h=replace(h,'/**\n * struct dwc3 -',types+'/**\n * struct dwc3 -')
 h=replace(h,' * @connect_mutex: for the pull-up and err_recovery_work\n',
  ' * @connect_mutex: for the pull-up, error recovery and detection window\n'
  ' * @detect_window: optional internal quiet window, state under lock\n'
  ' * @detect_generation: never-zero per-gadget window cookie sequence\n'
  ' * @detect_pm_busy: core PM transition excludes a new window\n'
  ' * @detect_system_blocked: system prepare through complete excludes begin\n'
  ' * @detect_stopping: UDC stop/removal excludes all new work\n')
 h=replace(h,'\tstruct mutex\t\tconnect_mutex;\n','\tstruct mutex\t\tconnect_mutex;\n'
  '\tstruct dwc3_gadget_window detect_window;\n\tu64 detect_generation;\n'
  '\tbool detect_pm_busy;\n\tbool detect_system_blocked;\n\tbool detect_stopping;\n')
 h=replace(h,'int dwc3_gadget_init(struct dwc3 *dwc);',
  'int dwc3_gadget_window_begin(struct dwc3 *dwc, struct dwc3_gadget_window_result *result);\n'
  'int dwc3_gadget_window_cancel(struct dwc3 *dwc, u64 cookie, struct dwc3_gadget_window_result *result);\n'
  'int dwc3_gadget_window_end(struct dwc3 *dwc, u64 cookie, struct dwc3_gadget_window_result *result);\n'
  'int dwc3_gadget_init(struct dwc3 *dwc);')
 # Used by core PM and gadget paths, under their existing short spin lock.
 anchor='/* power management interface */'
 h=replace(h,anchor,'''static inline bool dwc3_gadget_window_busy(struct dwc3 *dwc)
{
	enum dwc3_gadget_window_state state = READ_ONCE(dwc->detect_window.state);

	return state != DWC3_WINDOW_IDLE && state != DWC3_WINDOW_SHUTDOWN;
}

'''+anchor)
 (HERE/'core.h').write_text(h)

 g=(HERE/'baseline/gadget.c').read_text()
 old=function(g,'dwc3_gadget_pullup');new=old
 new=replace(new,'\tint\t\t\tret;','\tint\t\t\tret;\n\tunsigned long\t\tflags;')
 new=replace(new,'\tdwc->softconnect = is_on;','''	spin_lock_irqsave(&dwc->lock, flags);
	if (dwc->detect_stopping && is_on) {
		spin_unlock_irqrestore(&dwc->lock, flags);
		return -ESHUTDOWN;
	}
	dwc->softconnect = is_on;
	if (dwc3_gadget_window_busy(dwc)) {
		spin_unlock_irqrestore(&dwc->lock, flags);
		return 0; /* intent only; the explicit end reconciles it */
	}
	spin_unlock_irqrestore(&dwc->lock, flags);''')
 new=replace(new,'\tmutex_lock(&dwc->connect_mutex);\n\tif (!is_on)',
 '''	mutex_lock(&dwc->connect_mutex);
	/* begin may have claimed after this pullup's PM/IRQ preparation. */
	if (dwc3_gadget_window_busy(dwc) ||
	    (READ_ONCE(dwc->detect_stopping) && is_on)) {
		mutex_unlock(&dwc->connect_mutex);
		pm_runtime_put(dwc->dev);
		return 0;
	}
	is_on = dwc3_gadget_window_wanted(dwc);
	if (!is_on)''')
 g=replace(g,old,(HERE/'window-functions.c.txt').read_text()+'\n\n'+new)
 old=function(g,'dwc3_err_recovery_work')
 new='''static int dwc3_gadget_recover_locked(struct dwc3 *dwc)
{
	unsigned long flags;
	int ret;

	lockdep_assert_held(&dwc->connect_mutex);
	ret = dwc3_gadget_soft_disconnect(dwc);
	dwc3_disconnect_gadget_sleepable(dwc);
	if (ret)
		goto failed;
	if (dwc3_gadget_window_wanted(dwc)) {
		u32 count;

		synchronize_irq(dwc->irq_gadget);
		spin_lock_irqsave(&dwc->lock, flags);
		count = ++dwc->err_recovery_count;
		spin_unlock_irqrestore(&dwc->lock, flags);
		if (count > DWC3_ERR_RECOVERY_MAX) {
			ret = -EIO;
			goto failed;
		}
		ret = dwc3_gadget_soft_connect(dwc);
		if (ret)
			goto failed;
	}
	spin_lock_irqsave(&dwc->lock, flags);
	dwc->err_state = DWC3_ERR_NONE;
	spin_unlock_irqrestore(&dwc->lock, flags);
	return 0;
failed:
	dev_err(dwc->dev, "Unable to recover the controller\\n");
	spin_lock_irqsave(&dwc->lock, flags);
	dwc->err_state = DWC3_ERR_UNRECOVERABLE;
	spin_unlock_irqrestore(&dwc->lock, flags);
	return ret;
}

static void dwc3_err_recovery_work(struct work_struct *work)
{
	struct dwc3 *dwc = container_of(work, struct dwc3, err_recovery_work);

	mutex_lock(&dwc->connect_mutex);
	if (!READ_ONCE(dwc->detect_stopping)) {
		if (dwc3_gadget_window_busy(dwc))
			dwc->detect_window.recovery_pending = true;
		else
			dwc3_gadget_recover_locked(dwc);
	}
	mutex_unlock(&dwc->connect_mutex);
}'''
 g=replace(g,old,new)
 g=replace(g,'\tmutex_init(&dwc->connect_mutex);','\tmutex_init(&dwc->connect_mutex);\n'
   '\tmemset(&dwc->detect_window, 0, sizeof(dwc->detect_window));\n'
   '\tdwc->detect_stopping = false;')
 # Rebinding starts a fresh lifetime; old cookie generation is retained.
 g=replace(g,'\tdwc->gadget_driver\t= driver;',
   '\tmemset(&dwc->detect_window, 0, sizeof(dwc->detect_window));\n'
   '\tdwc->detect_stopping = false;\n\tdwc->gadget_driver\t= driver;')
 old=function(g,'dwc3_gadget_stop')
 new=replace(old,'\tif (dwc->sys_wakeup)','\tdwc3_gadget_window_shutdown(dwc);\n\n\tif (dwc->sys_wakeup)')
 g=replace(g,old,new)
 old=function(g,'dwc3_gadget_exit')
 new=replace(old,'\tcancel_work_sync(&dwc->err_recovery_work);','\tdwc3_gadget_window_shutdown(dwc);\n'
   '\tcancel_work_sync(&dwc->err_recovery_work);')
 new=replace(new,'\tcancel_work_sync(&dwc->err_recovery_work);\n','')
 new=replace(new,'\tmutex_destroy(&dwc->connect_mutex);\n','')
 new=replace(new,'\tusb_del_gadget(dwc->gadget);','\tusb_del_gadget(dwc->gadget);\n'
   '\tcancel_work_sync(&dwc->err_recovery_work);\n'
   '\tmutex_destroy(&dwc->connect_mutex);')
 g=replace(g,old,new)
 for name in ['dwc3_gadget_suspend','dwc3_gadget_resume']:
  old=function(g,name);new=old
  if name.endswith('suspend'):
   new=replace(new,'\tret = dwc3_gadget_soft_disconnect(dwc);',
    '\tif (dwc3_gadget_window_busy(dwc))\n\t\treturn -EBUSY;\n\n\tret = dwc3_gadget_soft_disconnect(dwc);')
  else:
   new=replace(new,'\tif (!dwc->gadget_driver',
    '\tif (dwc3_gadget_window_busy(dwc))\n\t\treturn -EBUSY;\n\n\tif (!dwc->gadget_driver')
  g=replace(g,old,new)
 (HERE/'gadget.c').write_text(g)

 c=(HERE/'baseline/core.c').read_text()
 anchor='static int dwc3_suspend_common(struct dwc3 *dwc, pm_message_t msg)'
 pm='''/* No PM callback can overlap a claimed window, and begin cannot claim
 * between this short gate and PHY/core teardown. PM acquisition is outside
 * connect_mutex; system prepare also fences a new begin through complete.
 */
static int dwc3_gadget_window_pm_enter(struct dwc3 *dwc)
{
	unsigned long flags;
	int ret = 0;

	spin_lock_irqsave(&dwc->lock, flags);
	if (dwc3_gadget_window_busy(dwc) || dwc->detect_pm_busy)
		ret = -EBUSY;
	else
		dwc->detect_pm_busy = true;
	spin_unlock_irqrestore(&dwc->lock, flags);
	return ret;
}

static void dwc3_gadget_window_pm_exit(struct dwc3 *dwc)
{
	unsigned long flags;

	spin_lock_irqsave(&dwc->lock, flags);
	dwc->detect_pm_busy = false;
	spin_unlock_irqrestore(&dwc->lock, flags);
}

'''
 c=replace(c,anchor,pm+anchor)
 for name in ['dwc3_suspend_common','dwc3_resume_common']:
  old=function(c,name);new=old
  import re
  match=re.search(r'^\tint\s+ret;$',new,re.M);assert match,name
  declarations=match[0]
  if name=='dwc3_resume_common':
   declarations+='\n\tu32\t\treg;\n\tint\t\ti;'
  new=replace(new,declarations,declarations+'\n\n\tret = dwc3_gadget_window_pm_enter(dwc);\n\tif (ret)\n\t\treturn ret;')
  # Preserve old error exits, releasing only the new transition gate.
  start=new.index('\tif (ret)\n\t\treturn ret;')+len('\tif (ret)\n\t\treturn ret;')
  new=new[:start]+new[start:].replace('return ret;','goto out;')
  assert new.endswith('\treturn 0;\n}')
  new=new[:-len('\treturn 0;\n}')]+ '\tret = 0;\nout:\n\tdwc3_gadget_window_pm_exit(dwc);\n\treturn ret;\n}'
  c=replace(c,old,new)
 old=function(c,'dwc3_pm_prepare');new=old
 new=replace(new,'\tstruct device *dev = dwc->dev;','''	struct device *dev = dwc->dev;
	unsigned long flags;
	int ret = 0;

	spin_lock_irqsave(&dwc->lock, flags);
	if (dwc3_gadget_window_busy(dwc) || dwc->detect_pm_busy)
		ret = -EBUSY;
	else
		dwc->detect_system_blocked = true;
	spin_unlock_irqrestore(&dwc->lock, flags);
	if (ret)
		return ret;''')
 c=replace(c,old,new)
 old=function(c,'dwc3_pm_complete');new=old
 new=replace(new,'\tu32\t\treg;','''	u32		reg;
	unsigned long flags;

	spin_lock_irqsave(&dwc->lock, flags);
	dwc->detect_system_blocked = false;
	spin_unlock_irqrestore(&dwc->lock, flags);''')
 c=replace(c,old,new)
 (HERE/'core.c').write_text(c)
 patch=''
 for name in ['core.h','core.c','gadget.c']:
  patch+=''.join(difflib.unified_diff((HERE/'baseline'/name).read_text().splitlines(True),
    (HERE/name).read_text().splitlines(True),fromfile='a/drivers/usb/dwc3/'+name,tofile='b/drivers/usb/dwc3/'+name))
 (HERE/'dwc-window.patch').write_text(patch)
 report={'files':{n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in ['core.h','core.c','gadget.c','dwc-window.patch']},
   'automatic_caller_installed':False,'pmic_or_phy_writes_added':False,'uapi_or_exports_added':False,
   'shared_source_modified':False,'phone_accessed':False}
 (HERE/'candidate-manifest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
