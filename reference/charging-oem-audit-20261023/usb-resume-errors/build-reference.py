"""Extract actual cached USB functions; compile fake-boundary fixtures only."""
from pathlib import Path
import difflib
import hashlib
import json
import re
import subprocess

root = Path(__file__).resolve().parent
paths = {
    'legacy': 'drivers--usb--dwc3--dwc3-qcom-legacy.c',
    'core': 'drivers--usb--dwc3--core.c',
    'gadget': 'drivers--usb--dwc3--gadget.c',
}
source = {name: (root / path).read_text() for name, path in paths.items()}
manifest = []


def extract(kind, name):
    text = source[kind]
    match = re.search(r'^(?:static )?int\s+' + name + r'\([^;]*?\)\n\{', text, re.M)
    assert match, name
    # Kernel function terminators occupy column zero. Nested blocks are indented.
    stop = text.index('\n}', match.start()) + 2
    value = text[match.start():stop]
    manifest.append({'source': paths[kind], 'function': name,
                     'line': text.count('\n', 0, match.start()) + 1,
                     'sha256': hashlib.sha256(value.encode()).hexdigest()})
    return value


functions = [
    extract('legacy', 'dwc3_qcom_suspend'),
    extract('legacy', 'dwc3_qcom_resume'),
    extract('core', 'dwc3_core_soft_reset'),
    extract('gadget', '__dwc3_gadget_start'),
    extract('gadget', 'dwc3_gadget_run_stop'),
    extract('gadget', 'dwc3_gadget_soft_disconnect'),
    extract('gadget', 'dwc3_gadget_soft_connect'),
    extract('gadget', 'dwc3_gadget_suspend'),
    extract('gadget', 'dwc3_gadget_resume'),
    extract('core', 'dwc3_resume_common'),
]
(root / 'reference-functions.inc').write_text('\n\n'.join(functions) + '\n')
(root / 'function-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')

diagnostic = dict(source)
diagnostic['legacy'] = diagnostic['legacy'].replace(
    'dev_err(qcom->dev, "port-%d HS-PHY not in L2\\n", i + 1);',
    'dev_err(qcom->dev, "port-%d HS-PHY not in L2: status=%#x wakeup=%d\\n",\n'
    '\t\t\ti + 1, val, wakeup);')
for indentation in ('\t\t', '\t\t\t'):
    before = indentation + 'dwc3_gadget_resume(dwc);'
    after = indentation + 'ret = dwc3_gadget_resume(dwc);\n' + \
        indentation + 'if (ret)\n' + indentation + \
        '\tdev_err(dwc->dev, "gadget resume failed: %d\\n", ret);'
    assert before in diagnostic['core']
    diagnostic['core'] = diagnostic['core'].replace(before, after, 1)
before = '\tdwc3_event_buffers_setup(dwc);\n\t__dwc3_gadget_start(dwc);\n\treturn dwc3_gadget_run_stop(dwc, true);'
assert source['gadget'].count(before) == 1
diagnostic['gadget'] = diagnostic['gadget'].replace(before,
    '\tdwc3_event_buffers_setup(dwc);\n\tret = __dwc3_gadget_start(dwc);\n'
    '\tif (ret)\n\t\tdev_err(dwc->dev, "gadget endpoint start failed: %d\\n", ret);\n'
    '\treturn dwc3_gadget_run_stop(dwc, true);', 1)

propagate = dict(source)
resume_name = 'static int dwc3_resume_common(struct dwc3 *dwc, pm_message_t msg)'
start = propagate['core'].index(resume_name)
end = propagate['core'].index('\n}', start) + 2
old = propagate['core'][start:end]
new = old.replace('int\t\tret;', 'int\t\tret = 0;', 1).replace(
    'dwc3_gadget_resume(dwc);', 'ret = dwc3_gadget_resume(dwc);')
assert new.count('return 0;') == 1
new = new.replace('\treturn 0;\n}',
    '\tif (ret)\n\t\tdev_err(dwc->dev, "gadget resume failed: %d\\n", ret);\n\n\treturn ret;\n}')
propagate['core'] = propagate['core'][:start] + new + propagate['core'][end:]
propagate['gadget'] = propagate['gadget'].replace(before,
    '\tdwc3_event_buffers_setup(dwc);\n\tret = __dwc3_gadget_start(dwc);\n'
    '\tif (ret) {\n\t\tdev_err(dwc->dev, "gadget endpoint start failed: %d\\n", ret);\n'
    '\t\treturn ret;\n\t}\n\treturn dwc3_gadget_run_stop(dwc, true);', 1)
# L2 status is left advisory in both variants: absence is not established fatal.
propagate['legacy'] = diagnostic['legacy']


def write_patch(name, changed):
    result = []
    for kind, original in source.items():
        path = {'legacy': 'drivers/usb/dwc3/dwc3-qcom-legacy.c',
                'core': 'drivers/usb/dwc3/core.c',
                'gadget': 'drivers/usb/dwc3/gadget.c'}[kind]
        result.extend(difflib.unified_diff(original.splitlines(True),
            changed[kind].splitlines(True), fromfile='a/' + path,
            tofile='b/' + path))
    (root / name).write_text(''.join(result))


write_patch('diagnostic-only.patch', diagnostic)
write_patch('propagate-errors.patch', propagate)
original_source = dict(source)
for label, variant in (('original', original_source), ('diagnostic', diagnostic),
                       ('propagate', propagate)):
    if label != 'original':
        source = variant
        variant_functions = [extract(kind, name) for kind, name in (
            ('legacy', 'dwc3_qcom_suspend'), ('legacy', 'dwc3_qcom_resume'),
            ('core', 'dwc3_core_soft_reset'), ('gadget', '__dwc3_gadget_start'),
            ('gadget', 'dwc3_gadget_run_stop'), ('gadget', 'dwc3_gadget_soft_disconnect'),
            ('gadget', 'dwc3_gadget_soft_connect'), ('gadget', 'dwc3_gadget_suspend'),
            ('gadget', 'dwc3_gadget_resume'), ('core', 'dwc3_resume_common'))]
        (root / ('reference-functions-' + label + '.inc')).write_text(
            '\n\n'.join(variant_functions) + '\n')
    command = ['cc', '-std=c11', '-g', '-O1', '-Wall', '-Wextra',
               '-Wno-unused-parameter', '-Werror', '-fsanitize=address,undefined',
               '-fno-omit-frame-pointer', '-DVARIANT_' + label.upper(),
               str(root / 'test-reference.c'), '-o', str(root / ('test-' + label))]
    subprocess.run(command, check=True)
    result = subprocess.run([str(root / ('test-' + label))], check=True,
                            text=True, capture_output=True)
    print(result.stdout.strip())
    (root / ('result-' + label + '.json')).write_text(result.stdout)

patch_checks = []
import tempfile
for patch_name in ('diagnostic-only.patch', 'propagate-errors.patch'):
    with tempfile.TemporaryDirectory(prefix='patch-check-', dir=root) as directory:
        tree = Path(directory)
        for kind, text in original_source.items():
            name = {'legacy': 'drivers/usb/dwc3/dwc3-qcom-legacy.c',
                    'core': 'drivers/usb/dwc3/core.c',
                    'gadget': 'drivers/usb/dwc3/gadget.c'}[kind]
            target = tree / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)
        result = subprocess.run(['patch', '--dry-run', '-p1', '-i', str(root / patch_name)],
                                cwd=tree, capture_output=True, text=True, check=True)
        patch_checks.append({'patch': patch_name, 'dry_run_passed_on_private_copy': True})
(root / 'patch-check-result.json').write_text(json.dumps(patch_checks, indent=2) + '\n')
