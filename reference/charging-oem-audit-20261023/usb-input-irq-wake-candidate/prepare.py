"""Add balanced native IRQ wake references to the installed USB source."""
from pathlib import Path
import difflib,hashlib,json,re
HERE=Path(__file__).resolve().parent;BASE=HERE.parent/'usb-input-pm-notify-candidate'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def function(text,name):
 m=re.search(r'^static [^\n]+\b'+name+r'\(',text,re.M);assert m,name
 start=m.start();brace=text.index('{',m.end());depth=1;pos=brace+1
 while depth:
  if text[pos]=='{':depth+=1
  if text[pos]=='}':depth-=1
  pos+=1
 return text[start:pos]
def once(source,before,after):
 assert source.count(before)==1,before[:100];return source.replace(before,after)
def main():
 old_raw=(BASE/'samurai-usb-input.c').read_bytes();assert sha(old_raw)=='4bc1f53e40b04ac52620a9dedb641799b479de9034c3b658d0d1f3435c4d95d3'
 old=old_raw.decode().replace('\r\n','\n')
 new=once(old,'#include <linux/pm.h>','#include <linux/pm.h>\n#include <linux/pm_wakeup.h>')
 new=once(new,'struct samurai_usb_input {','struct samurai_usb_input {\n\tstruct device *event_dev;\n\tint event_irqs[2];\n\tunsigned long wake_armed;')
 helpers='''static int samurai_usb_clear_wake(struct samurai_usb_input *input)
{
\tint i, ret, first = 0;

\tfor (i = ARRAY_SIZE(input->event_irqs) - 1; i >= 0; i--) {
\t\tif (!(input->wake_armed & BIT(i)))
\t\t\tcontinue;
\t\tret = disable_irq_wake(input->event_irqs[i]);
\t\tif (ret) {
\t\t\tif (!first)
\t\t\t\tfirst = ret;
\t\t\tcontinue;
\t\t}
\t\tinput->wake_armed &= ~BIT(i);
\t}
\treturn first;
}

static int samurai_usb_arm_wake(struct samurai_usb_input *input)
{
\tint i, ret;

\t/* The existing PSY wakeup switch owns this policy. Legacy software
\t * devices have no IRQ pair and retain their polling-only behavior.
\t */
\tif (!input->psy || !device_may_wakeup(&input->psy->dev))
\t\treturn 0;
\tfor (i = 0; i < ARRAY_SIZE(input->event_irqs); i++) {
\t\tif (input->event_irqs[i] <= 0)
\t\t\tcontinue;
\t\tret = enable_irq_wake(input->event_irqs[i]);
\t\tif (ret)
\t\t\treturn ret;
\t\tinput->wake_armed |= BIT(i);
\t}
\treturn 0;
}

static void samurai_usb_restart_work(struct samurai_usb_input *input)
{
\tmutex_lock(&input->lock);
\tinput->udc_valid = false;
\tinput->paused = false;
\tmutex_unlock(&input->lock);
\tmod_delayed_work(system_wq, &input->work, 0);
}

static void samurai_usb_cleanup_wake(void *data)
{
\tstruct samurai_usb_input *input = data;
\tint ret = samurai_usb_clear_wake(input);

\tif (ret)
\t\tdev_warn(input->event_dev, "USB wake IRQ cleanup failed: %d\\n", ret);
}

'''
 suspend='''static int samurai_usb_suspend(struct device *dev)
{
\tstruct samurai_usb_input *input = dev_get_drvdata(dev);
\tint ret, cleanup;

\t/* A failed earlier disarm must not accumulate another wake reference. */
\tret = samurai_usb_clear_wake(input);
\tif (ret)
\t\treturn ret;
\tsamurai_usb_stop(input);
\tret = samurai_usb_arm_wake(input);
\tif (ret) {
\t\tcleanup = samurai_usb_clear_wake(input);
\t\tif (cleanup)
\t\t\tdev_warn(dev, "USB wake IRQ unwind failed: %d\\n", cleanup);
\t\t/* The PM core need not resume a device whose suspend failed. */
\t\tsamurai_usb_restart_work(input);
\t}
\treturn ret;
}'''
 resume='''static int samurai_usb_resume(struct device *dev)
{
\tstruct samurai_usb_input *input = dev_get_drvdata(dev);
\tint ret = samurai_usb_clear_wake(input);

\t/* Resume normal budget discovery even if disarming reports an error. */
\tsamurai_usb_restart_work(input);
\treturn ret;
}'''
 new=once(new,function(new,'samurai_usb_suspend'),helpers+suspend)
 new=once(new,function(new,'samurai_usb_resume'),resume)
 request=function(new,'samurai_usb_request_events')
 request=once(request,'\t\tif (ret)\n\t\t\treturn ret;\n\t}\n\treturn 0;', '\t\tif (ret)\n\t\t\treturn ret;\n\t\tinput->event_irqs[i] = irqs[i];\n\t}\n\treturn 0;')
 new=once(new,function(new,'samurai_usb_request_events'),request)
 new=once(new,'\tinput->map = dev_get_regmap(dev->parent, NULL);','\tinput->event_dev = dev;\n\tinput->map = dev_get_regmap(dev->parent, NULL);')
 new=once(new,'\t/* LIFO devres: stop polling before the supply and PMIC map are released. */','\t/* LIFO: stop work, disarm owned IRQ wake refs, then release the PSY. */\n\tret = devm_add_action_or_reset(dev, samurai_usb_cleanup_wake, input);\n\tif (ret)\n\t\treturn ret;')
 shutdown='''static void samurai_usb_shutdown(struct platform_device *pdev)
{
\tstruct samurai_usb_input *input = platform_get_drvdata(pdev);

\tsamurai_usb_stop(input);
\tsamurai_usb_cleanup_wake(input);
}'''
 new=once(new,function(new,'samurai_usb_shutdown'),shutdown)
 changed=['samurai_usb_suspend','samurai_usb_resume','samurai_usb_request_events','samurai_usb_probe','samurai_usb_shutdown']
 unchanged=[]
 for name in re.findall(r'^static [^\n]+\b(samurai_usb_\w+)\(',old,re.M):
  if name not in changed:assert function(old,name)==function(new,name),name;unchanged.append(name)
 for name in ['samurai-usb-input-decode.h','native-pm-link.c.inc']:
  raw=(BASE/name).read_bytes();assert not (HERE/name).exists();(HERE/name).write_bytes(raw)
 assert not (HERE/'samurai-usb-input.c').exists();(HERE/'samurai-usb-input.c').write_text(new)
 (HERE/'irq-wake.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/samurai-usb-input.c',tofile='b/samurai-usb-input.c')))
 source=Path('/home/cy122/charging-management-20261023/dwc-image504-budget-fence-01/source354')
 references={}
 for name in ['drivers/spmi/spmi-pmic-arb.c','kernel/irq/pm.c','include/linux/interrupt.h','include/linux/pm_wakeup.h']:
  raw=(source/name).read_bytes();references[name]=dict(sha256=sha(raw),bytes=len(raw))
 result=dict(passed=True,base_source_sha256=sha(old_raw),candidate_source_sha256=sha(new.encode()),decoder_sha256=sha((HERE/'samurai-usb-input-decode.h').read_bytes()),
  base_CRLF_normalized_for_function_text_comparison=True,
  changed_functions=changed,unchanged_functions=unchanged,added_functions=['samurai_usb_clear_wake','samurai_usb_arm_wake','samurai_usb_restart_work','samurai_usb_cleanup_wake'],
  primary_Image504_source_references=references,reason='pmic_arb MASK_ON_SUSPEND; irq_set_wake delegates to parent, current provider never requests wake',
  PSY_wakeup_switch_respected=True,partial_arm_unwind_and_failed_suspend_restart=True,failed_disarm_bits_retained_and_no_double_arm=True,
  cleanup_before_PSY_and_IRQ_release=True,budget_notification_and_real_event_handlers_unchanged=True,charger_or_PMIC_policy_registers_written=False,
  device_accessed=False,physical_USB_wakeup_accepted=False)
 (HERE/'source-result.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:result[k] for k in ['passed','candidate_source_sha256','changed_functions','unchanged_functions']}))
if __name__=='__main__':main()
