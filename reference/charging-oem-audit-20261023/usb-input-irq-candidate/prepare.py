"""Add OEM USB IRQ-triggered reads to the exact deployed R7 provider."""
from pathlib import Path
import difflib
import hashlib
import json

HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
original = REF / 'charging-management-20261023/samurai-usb-input.c'
decoder = REF / 'charging-oem-audit-20261023/source-float-candidate/samurai-usb-input-decode.h'
if sha(original) != 'b712764fbd4ab24475ae1ba030ee4c26c7eb048a6038488a5435b44ef7eb7098':
    raise RuntimeError('not the actual deployed R7 source')
if sha(decoder) != 'a17caa2cbeb2352da249474e0265fa96745f544d96a29d0ebe8f14c656d548fd':
    raise RuntimeError('not the actual deployed FLOAT decoder')
baseline = original.read_text()
text = baseline.replace('#include <linux/module.h>', '#include <linux/module.h>\n#include <linux/interrupt.h>')
events = r'''
/* IRQs only expedite the existing stable-read/policy path. No budget or
 * attachment is inferred from an interrupt, and no charging register is set.
 */
static irqreturn_t samurai_usb_event(int irq, void *data)
{
	struct samurai_usb_input *input = data;

	mutex_lock(&input->lock);
	if (!input->paused)
		mod_delayed_work(system_wq, &input->work, 0);
	mutex_unlock(&input->lock);
	return IRQ_HANDLED;
}

static int samurai_usb_request_events(struct platform_device *pdev,
				      struct samurai_usb_input *input)
{
	static const char * const names[] = { "usbin-plugin", "usbin-src-change" };
	int irqs[ARRAY_SIZE(names)], i, ret;

	/* A legacy software device has no IRQ resources. Keep its existing 1s
	 * fallback; only a complete named DT pair enables event-driven reads.
	 */
	for (i = 0; i < ARRAY_SIZE(names); i++) {
		irqs[i] = platform_get_irq_byname_optional(pdev, names[i]);
		if (irqs[i] == -EPROBE_DEFER)
			return -EPROBE_DEFER;
	}
	if ((irqs[0] == -ENXIO || irqs[0] == -ENODEV) &&
	    (irqs[1] == -ENXIO || irqs[1] == -ENODEV))
		return 0;
	for (i = 0; i < ARRAY_SIZE(names); i++) {
		if (irqs[i] <= 0)
			return irqs[i] < 0 ? irqs[i] : -EINVAL;
	}
	if (irqs[0] == irqs[1])
		return -EINVAL;
	/* Requested while paused, before publishing the power_supply. A probe
	 * failure therefore cannot queue work against an unpublished supply.
	 */
	for (i = 0; i < ARRAY_SIZE(names); i++) {
		ret = devm_request_threaded_irq(&pdev->dev, irqs[i], NULL,
						samurai_usb_event, IRQF_ONESHOT,
						names[i], input);
		if (ret)
			return ret;
	}
	return 0;
}

'''
anchor = 'static int samurai_usb_probe(struct platform_device *pdev)'
if text.count(anchor) != 1:
    raise RuntimeError('probe anchor changed')
text = text.replace(anchor, events + anchor)
old = '\tINIT_DELAYED_WORK(&input->work, samurai_usb_poll);\n\tconfig.drv_data = input;'
new = ('\tINIT_DELAYED_WORK(&input->work, samurai_usb_poll);\n'
       '\tinput->paused = true;\n'
       '\tret = samurai_usb_request_events(pdev, input);\n'
       '\tif (ret)\n\t\treturn dev_err_probe(dev, ret, "USB input events\\n");\n'
       '\tconfig.drv_data = input;')
if text.count(old) != 1:
    raise RuntimeError('initialization anchor changed')
text = text.replace(old, new)
old = '\tschedule_delayed_work(&input->work, 0);\n\tsamurai_usb_retain_for_native_consumer(dev);'
new = ('\tmutex_lock(&input->lock);\n\tinput->paused = false;\n'
       '\tschedule_delayed_work(&input->work, 0);\n\tmutex_unlock(&input->lock);\n'
       '\tsamurai_usb_retain_for_native_consumer(dev);')
if text.count(old) != 1:
    raise RuntimeError('start anchor changed')
text = text.replace(old, new)
old = '\tstruct device *child;\n\tint ret = platform_driver_register'
new = '\tstruct device *child;\n\tstruct device_node *node;\n\tint ret = platform_driver_register'
if text.count(old) != 1:
    raise RuntimeError('board locator anchor changed')
text = text.replace(old, new)
old = '\tif (!of_machine_is_compatible("realme,samurai")) { ret = -ENODEV; goto fail; }\n\tchild = '
new = ('\tif (!of_machine_is_compatible("realme,samurai")) { ret = -ENODEV; goto fail; }\n'
       '\t/* A real enabled DT device is populated by its PMIC parent. Do not\n'
       '\t * create a second same-named supply from register_board=1.\n\t */\n'
       '\tnode = of_find_compatible_node(NULL, NULL, "realme,rmx1931-usb-input");\n'
       '\tif (node) {\n\t\tbool available = of_device_is_available(node);\n'
       '\t\tof_node_put(node);\n\t\tif (available)\n\t\t\treturn 0;\n\t}\n'
       '\tchild = ')
if text.count(old) != 1:
    raise RuntimeError('board creation anchor changed')
text = text.replace(old, new)
old = 'static const struct of_device_id samurai_usb_match[] = {'
new = ('''/* Normal reboot does not unwind devres. Stop work before the PMIC parent
 * shuts down; the remaining IRQ threads see paused and cannot requeue it.
 */
static void samurai_usb_shutdown(struct platform_device *pdev)
{
\tsamurai_usb_stop(platform_get_drvdata(pdev));
}

''' + old)
if text.count(old) != 1:
    raise RuntimeError('shutdown insertion anchor changed')
text = text.replace(old, new)
old = '\t.probe = samurai_usb_probe,\n\t.driver = {'
new = '\t.probe = samurai_usb_probe,\n\t.shutdown = samurai_usb_shutdown,\n\t.driver = {'
if text.count(old) != 1:
    raise RuntimeError('shutdown registration anchor changed')
text = text.replace(old, new)
for name, raw in [('baseline-samurai-usb-input.c', baseline), ('samurai-usb-input.c', text)]:
    (HERE / name).write_text(raw)
(HERE / decoder.name).write_bytes(decoder.read_bytes())
(HERE / 'irq-events.inc').write_text(events)
patch = ''.join(difflib.unified_diff(baseline.splitlines(True), text.splitlines(True),
                fromfile='a/drivers/power/supply/samurai-usb-input.c',
                tofile='b/drivers/power/supply/samurai-usb-input.c'))
(HERE / 'usb-events.patch').write_text(patch)
dt = '''/* Add to the board DTS; uses the existing SPMI IRQ controller. */
&spmi_bus {
	pmic@2 {
		samurai_usb_input: usb-input@1300 {
			compatible = "realme,rmx1931-usb-input";
			reg = <0x1300>;
			interrupts = <0x2 0x13 0x4 IRQ_TYPE_EDGE_BOTH>,
				     <0x2 0x13 0x6 IRQ_TYPE_EDGE_RISING>;
			interrupt-names = "usbin-plugin", "usbin-src-change";
			status = "okay";
		};
	};
};
'''
(HERE / 'board-irq.fragment.dts').write_text(dt)
result = {'scope': 'unbuilt, undeployed USB input IRQ candidate only',
          'baseline_source_sha256': sha(original), 'decoder_unchanged_sha256': sha(decoder),
          'candidate_source_sha256': sha(HERE / 'samurai-usb-input.c'),
          'oem_irq_source': 'apsd-lifecycle/oem/arch--arm64--boot--dts--19781--pm8150b.dtsi:515-536',
          'IRQ_payload_does_not_assert_source_or_budget': True,
          'normal_shutdown_uses_existing_stop': True,
          'normal_poll_and_stable_decoder_preserved': True,
          'no_device_or_shared_source_changes': True}
(HERE / 'source-result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
