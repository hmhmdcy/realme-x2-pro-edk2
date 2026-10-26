"""Materialize the independent lifetime candidate from the private review draft."""
from pathlib import Path
import difflib
import hashlib
import json

HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel455')
PRIVATE.mkdir(exist_ok=True)
original = (HERE.parent / 'kernel453/bu64253.c').read_text()
text = Path('/mnt/e/edk2-samurai-out/kernel453/schema/bu64253-lifetime-quarantine-review-private.c').read_text()

def change(old, new):
    global text
    assert text.count(old) == 1, old
    text = text.replace(old, new)

change(' * ROHM BU64253 factory VCM protocol: in-tree k363 Werror and host C\n * ASAN/UBSAN checked. DT/schema, kernel PM integration and hardware pending.',
       ' * ROHM BU64253 independent lifetime candidate. Requires V4L2 core fix 0064.\n * Validation is recorded alongside this source; no hardware acceptance implied.')
text = text.replace('quarantine_entry', 'instance_entry').replace('bu64253_quarantine_lock', 'bu64253_instances_lock').replace('bu64253_quarantine', 'bu64253_instances')
change('\tbool supply_enabled;\n', '\tbool supply_enabled;\n\tbool power_module_ref;\n\tbool quarantined;\n')
change('/* Review-only policy: an unremoved VDD reference is quarantined until reboot.\n * There is deliberately no retry worker, force-disable or automatic PM reset.\n * This policy still needs product review before this draft can be deployed.\n */',
'''/* All generations remain listed until final destruction, so a late FD or a
 * quarantined powered generation blocks same-device rebind. Failed VDD-off is
 * retained until reboot: no retry worker, force-disable or automatic PM reset.
 * The power module reference is acquired BEFORE regulator_enable, never remove.
 */''')
change('\t/* A powered object retains its driver reference in the quarantine list. */\n\tWARN_ON(lens->supply_enabled);',
'''\t/* The detach failure path must retain its base kref. Never put an enabled
\t * regulator even if a future caller breaks that reference invariant.
\t */
\tif (WARN_ON(lens->supply_enabled || lens->power_module_ref))
\t\treturn;''')
change('\tput_device(lens->dev);\n\tkfree(lens);',
'''\tmutex_lock(&bu64253_instances_lock);
\tif (!list_empty(&lens->instance_entry))
\t\tlist_del(&lens->instance_entry);
\tmutex_unlock(&bu64253_instances_lock);
\tput_device(lens->dev);
\tkfree(lens);''')
change('\tlens->supply_enabled = false;\n\tmodule_put(THIS_MODULE);\n\t/* Retained OEM VAF-off sequence has a 1 ms delay, not an ID handshake. */\n\tusleep_range(1000, 1100);',
'''\tlens->supply_enabled = false;
\t/* Retained OEM VAF-off sequence has a 1 ms delay, not an ID handshake. */
\tusleep_range(1000, 1100);
\tlens->power_module_ref = false;
\tmodule_put(THIS_MODULE);''')
change('\tret = regulator_enable(lens->vdd);\n\tif (ret) {\n\t\tmodule_put(THIS_MODULE);',
'''\tlens->power_module_ref = true;
\tret = regulator_enable(lens->vdd);
\tif (ret) {
\t\tlens->power_module_ref = false;
\t\tmodule_put(THIS_MODULE);''')
change('\t\tmutex_lock(&bu64253_instances_lock);\n\t\tlist_add_tail(&lens->instance_entry, &bu64253_instances);\n\t\tmutex_unlock(&bu64253_instances_lock);\n\t\treturn;',
       '\t\tlens->quarantined = true;\n\t\treturn;')
change('\tstruct bu64253 *lens, *quarantined;', '\tstruct bu64253 *lens, *existing;')
old = '''\tmutex_lock(&bu64253_instances_lock);
\tlist_for_each_entry(quarantined, &bu64253_instances, instance_entry) {
\t\tif (quarantined->dev == dev) {
\t\t\tmutex_unlock(&bu64253_instances_lock);
\t\t\treturn dev_err_probe(dev, -EBUSY, "VDD fault quarantined until reboot\\n");
\t\t}
\t}
\tmutex_unlock(&bu64253_instances_lock);
'''
change(old, '')
change('\tmutex_init(&lens->lifecycle_lock);\n\tret = bu64253_load_init(dev, lens);',
'''\tmutex_init(&lens->lifecycle_lock);
\tmutex_lock(&bu64253_instances_lock);
\tlist_for_each_entry(existing, &bu64253_instances, instance_entry) {
\t\tif (existing->dev == dev) {
\t\t\tmutex_unlock(&bu64253_instances_lock);
\t\t\tret = -EBUSY;
\t\t\tdev_err_probe(dev, ret, "previous lens generation still retained\\n");
\t\t\tgoto put_lens;
\t\t}
\t}
\tlist_add_tail(&lens->instance_entry, &bu64253_instances);
\tmutex_unlock(&bu64253_instances_lock);
\tret = bu64253_load_init(dev, lens);''')
assert '__module_get' not in text
assert original == (HERE.parent / 'kernel453/bu64253.c').read_text()
(HERE / 'bu64253.c').write_text(text)
patch = ''.join(difflib.unified_diff(original.splitlines(True), text.splitlines(True),
    fromfile='a/drivers/media/i2c/bu64253.c', tofile='b/drivers/media/i2c/bu64253.c'))
(HERE / 'bu64253-lifetime-r3.patch').write_text(patch)
for name in ['imx319-bu64253-init.bin', 's5k3m5sx-bu64253-init.bin']:
    (PRIVATE / name).write_bytes((PRIVATE.parent / 'kernel453' / name).read_bytes())
report = dict(stage=455, candidate='BU64253 lifetime r3',
              prior_source_sha256=hashlib.sha256(original.encode()).hexdigest(),
              source_sha256=hashlib.sha256(text.encode()).hexdigest(),
              requires_core_0064_first=True, driver_base_ref_until_detach=True,
              framework_ref_per_successful_registered_and_release=True,
              device_ref_and_deferred_ctrl_mutex_regulator_release=True,
              all_retained_generations_block_same_device_rebind=True,
              late_close_skips_pm_after_remove=True,
              module_pin_acquired_before_enable_and_held_until_disable_success=True,
              disable_failure_retains_regulator_object_device_module_and_base_ref=True,
              no_new_module_pin_in_remove=True, quarantine_until_reboot_may_remain_powered=True,
              production_453_source_changed=False, sdk_or_phone_accessed=False,
              status='design materialized; compile and actual-C host checks recorded separately')
(HERE / 'design-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
