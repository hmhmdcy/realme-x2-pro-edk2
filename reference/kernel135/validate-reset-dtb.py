from pathlib import Path
import json
import hashlib
import subprocess
import sys
import os
import libfdt
import yaml
r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel135'
out = Path('/mnt/e/edk2-samurai-out/kernel135')
k = Path('/home/cy122/pmos-samurai-build134/usb134/kernel')
bin = Path(sys.executable).parent
mdss = '/soc@0/display-subsystem@ae00000'
dispcc = '/soc@0/clock-controller@af00000'
def tree(path):
    f = libfdt.Fdt(path.read_bytes())
    answer = {}
    def walk(offset, name):
        props = {}
        p = f.first_property_offset(offset, quiet=(libfdt.NOTFOUND,))
        while p >= 0:
            prop = f.get_property_by_offset(p)
            props[prop.name] = bytes(prop)
            p = f.next_property_offset(p, quiet=(libfdt.NOTFOUND,))
        answer[name] = props
        child = f.first_subnode(offset, quiet=(libfdt.NOTFOUND,))
        while child >= 0:
            walk(child, name.rstrip('/') + '/' + f.get_name(child))
            child = f.next_subnode(child, quiet=(libfdt.NOTFOUND,))
    walk(0, '/')
    return answer
old = tree(out.parent / 'kernel134/DTB-k134-private')
new = tree(out / 'DTB-k135-private')
assert old.keys() == new.keys()
differences = []
for node in old:
    for prop in old[node].keys() | new[node].keys():
        if old[node].get(prop) != new[node].get(prop):
            differences.append((node, prop))
assert differences == [(mdss, 'resets')]
assert new[dispcc]['compatible'] == b'qcom,sm8150-dispcc\0'
assert int.from_bytes(new[dispcc]['#reset-cells'], 'big') == 1
assert new[mdss]['resets'] == new[dispcc]['phandle'] + bytes(4)
assert int.from_bytes(new[dispcc]['reg'][4:8], 'big') == 0x0af00000
for header in ['qcom,dispcc-sm8150.h', 'qcom,dispcc-sm8250.h']:
    text = (k / 'include/dt-bindings/clock' / header).read_text()
    assert any(l.split() == ['#define', 'DISP_CC_MDSS_CORE_BCR', '0'] for l in text.splitlines())
driver = (k / 'drivers/clk/qcom/dispcc-sm8250.c').read_text()
assert '[DISP_CC_MDSS_CORE_BCR] = { 0x2000 }' in driver
assert '.resets = disp_cc_sm8250_resets' in driver
assert '.compatible = "qcom,sm8150-dispcc"' in driver
native = (k / 'drivers/gpu/drm/msm/msm_mdss.c').read_text()
assert native.index('ret = msm_mdss_reset(&pdev->dev);') < native.index('msm_mdss = devm_kzalloc')
assert 'reset_control_get_optional_exclusive(dev, NULL)' in native and 'msleep(20)' in native
binding = k / 'Documentation/devicetree/bindings/display/msm/qcom,sm8150-mdss.yaml'
common = binding.parent / 'mdss-common.yaml'
assert yaml.safe_load(common.read_text())['properties']['resets'] == {'items': [{'description': 'MDSS_CORE reset'}]}
processed = out / 'processed-mdss-private.json'
records = []
def command(name, args):
    p = subprocess.run([str(a) for a in args], capture_output=True, text=True, timeout=120, env=dict(os.environ, TMPDIR=str(out)))
    text = p.stdout + p.stderr
    (out / (name + '-private.log')).write_text(text)
    records.append(dict(name=name, exit=p.returncode, diagnostic_bytes=len(text.encode())))
    assert p.returncode == 0, (name, p.returncode)
    return text
assert command('schema-compile', [bin / 'dt-mk-schema', '-j', '-o', processed, binding, common]) == ''
diag = []
for name, path in [('before', out.parent / 'kernel134/DTB-k134-private'), ('after', out / 'DTB-k135-private')]:
    diag.append(command('schema-' + name, [bin / 'dt-validate', '-s', processed, '-l', 'qcom,sm8150-mdss', path]))
# Preserve inherited diagnostics, and reject any new diagnostic introduced by resets.
normalized = [text.replace(str(out.parent / 'kernel134/DTB-k134-private'), 'BOARD').replace(str(out / 'DTB-k135-private'), 'BOARD') for text in diag]
assert normalized[0] == normalized[1]
assert 'resets' not in normalized[1]
report = dict(stage=135, software_generation=134, release='7.3.0-rc6-rmx1931-samurai-k134+',
    isolated_dtb_build_pass=True, full_tree_nodes=len(new), exactly_one_property_added=True,
    changed_node=mdss, changed_property='resets', reset_provider=dispcc, reset_index=0,
    reset_provider_hardware_map_verified=True, native_probe_reset_precedes_child_binding=True,
    schema_checks=records, new_schema_diagnostics=0, inherited_schema_diagnostic_bytes=len(normalized[0].encode()),
    dtb_sha256=hashlib.sha256((out / 'DTB-k135-private').read_bytes()).hexdigest(),
    kernel_image_modules_rootfs_reused_from134=True, original134_source_and_dtb_preserved=True,
    deployed=False, boot_fix_accepted=False, gpu_fault_fixed=False, goal_complete=False)
(ref / 'dtb-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report), flush=True)
