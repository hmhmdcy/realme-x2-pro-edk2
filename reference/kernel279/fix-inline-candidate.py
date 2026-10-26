"""Adapt the maintained VFE170 backend to the imported public output model.

Does not enable the unimplemented VFE170 PIX pipeline or deploy anything.
"""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parent
TREE = Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
BUILD = Path('/home/cy122/x2pro-linux/camera279-isp-build-r1')
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel279')
assert json.loads((PRIVATE / 'candidate-build-state-private.json').read_text())['terminal']
before = subprocess.check_output(['git', '-C', str(TREE), 'diff'], text=True)
(PRIVATE / 'rebased-rfc-before-fixes.patch').write_text(before)
changes = []


def change(name, transform):
    path = TREE / name
    old = path.read_text()
    new = transform(old)
    assert old != new
    changes.append(dict(path=name, before_sha256=hashlib.sha256(old.encode()).hexdigest(),
                        after_sha256=hashlib.sha256(new.encode()).hexdigest()))
    path.write_text(new)


def function(text, signature, new):
    start = text.index(signature)
    end = text.index('\n}\n', start) + 3
    return text[:start] + new + text[end:]


def vfe170(text):
    # Unlike gen1, RDI bus clients are fixed by hardware, not freely allocated.
    text = function(text, 'static int vfe_get_output(', '')
    assert text.count('ret = vfe_get_output(line);') == 1
    text = text.replace('ret = vfe_get_output(line);', 'ret = vfe_get_output_v2(line);')
    text = text.replace('vfe_bus_status[VFE_LINE_NUM_MAX]', 'vfe_bus_status[3]')
    old = 'for (i = VFE_LINE_RDI0; i < vfe->res->line_num; i++) {\n\t\tvfe_bus_status[i]'
    assert text.count(old) == 1
    text = text.replace(old, 'for (i = 0; i < ARRAY_SIZE(vfe_bus_status); i++) {\n\t\tvfe_bus_status[i]')
    old = '\tstruct vfe_line *line = &vfe->line[vfe->wm_output_map[wm]];'
    assert text.count(old) == 1
    text = text.replace(old, '\tstruct vfe_line *line;')
    old = '\tif (vfe->wm_output_map[wm] == VFE_LINE_NONE) {'
    assert text.count(old) == 1
    text = text.replace(old, '\tif (wm >= ARRAY_SIZE(vfe->wm_output_map) ||\n'
                            '\t    vfe->wm_output_map[wm] < VFE_LINE_RDI0 ||\n'
                            '\t    vfe->wm_output_map[wm] >= vfe->res->line_num) {')
    old = '\toutput = &vfe->line[vfe->wm_output_map[wm]].output[0];'
    assert text.count(old) == 1
    text = text.replace(old, '\tline = &vfe->line[vfe->wm_output_map[wm]];\n'
                            '\toutput = &line->output[0];')
    return text


change('drivers/media/platform/qcom/camss/camss-vfe-17x.c', vfe170)


def resources(text):
    start = text.index('static const struct camss_subdev_resources vfe_res_8150[]')
    end = text.index('\n};', start)
    block = text[start:end]
    assert block.count('.line_num = 4') == 2
    assert block.count('.formats_pix = &vfe_formats_pix_845') == 2
    block = block.replace('.line_num = 4', '.line_num = 3')
    block = block.replace('.formats_pix = &vfe_formats_pix_845',
                          '.formats_pix = &vfe_formats_rdi_845')
    return text[:start] + block + text[end:]


change('drivers/media/platform/qcom/camss/camss.c', resources)
change('drivers/media/platform/qcom/camss/camss-vfe.c',
       lambda text: function(text, 'static bool __vfe_pix_fmt_is_raw(', ''))
(ROOT / 'vfe170-import-fix-validation.json').write_text(json.dumps(dict(
    stage=279, changes=changes, fixes=['fixed RDI bus-client mapping',
    'three hardware bus IRQ banks independent of video line count',
    'validate WM and line before indexing or forming a line pointer',
    'do not expose unsupported SM8150 PIX as fourth RDI',
    'remove unused RFC helper'],
    vfe170_hardware_isp_enabled=False, phone_unchanged=True), indent=2) + '\n')
print(json.dumps(changes, indent=2))
