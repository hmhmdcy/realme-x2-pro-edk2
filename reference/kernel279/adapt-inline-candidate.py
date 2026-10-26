"""Explicit rebases of reviewed RFC hunks onto the current maintained source."""
from pathlib import Path
import json
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
LOCK = ROOT / 'inline-candidate-apply-validation.json'
state = json.loads(LOCK.read_text())
tree = Path(state['candidate'])
number = int(sys.argv[1])
assert state['first_conflict']['number'] == number
patch = Path('/mnt/e/edk2-samurai-out/kernel279/posted-patches') / f'{number:02d}.patch'


def replace(path, old, new):
    path = tree / path
    text = path.read_text()
    assert text.count(old) == 1, (path, old)
    path.write_text(text.replace(old, new))


if number == 10:
    name = 'Documentation/userspace-api/media/v4l/meta-formats.rst'
    subprocess.run(['git', '-C', str(tree), 'apply', '--exclude=' + name, str(patch)], check=True)
    replace(name, '    metafmt-pisp-fe\n', '    metafmt-pisp-fe\n    metafmt-qcom-isp\n')
    note = 'Preserve newer rppx1 metadata format entry; add qcom immediately after pisp-fe.'
elif number == 15:
    name = 'drivers/media/platform/qcom/camss/camss-csid.c'
    subprocess.run(['git', '-C', str(tree), 'apply', '--exclude=' + name, str(patch)], check=True)
    path = tree / name
    text = path.read_text()
    assignment = '\t\tcsid->phy.need_vc_update = true;\n\n'
    assert text.count(assignment) == 2
    path.write_text(text.replace(assignment, ''))
    replace(name, '\tif (csid->phy.need_vc_update) {\n'
                  '\t\tcsid->res->hw_ops->configure_stream(csid, enable);\n'
                  '\t\tcsid->phy.need_vc_update = false;\n\t}\n',
                  '\tcsid->res->hw_ops->configure_stream(csid, enable);\n')
    note = 'Preserve maintained regulator/parent runtime-PM failure cleanup; configure CSID on every s_stream.'
elif number == 19:
    name = 'drivers/media/platform/qcom/camss/camss-vfe.c'
    subprocess.run(['git', '-C', str(tree), 'apply', '--exclude=' + name, str(patch)], check=True)
    path = tree / name
    text = path.read_text()
    for old, new in [('line->output', 'line->output[0]'),
                     ('].output', '].output[0]'), ('l->output.', 'l->output[0].')]:
        assert old in text
        text = text.replace(old, new)
    path.write_text(text)
    replace(name, '\t\tl->id = i;\n',
                  '\t\tl->id = i;\n\n\t\tl->num_outputs = 1;\n\t\tl->output[0].line = l;\n\n')
    # SOF tagging is a maintained VFE170 extension absent in the RFC base.
    name = 'drivers/media/platform/qcom/camss/camss-vfe-17x.c'
    replace(name, '\toutput = &vfe->line[line_id].output;\n',
                  '\toutput = &vfe->line[line_id].output[0];\n')
    note = 'Preserve maintained queue rejection/cleanup and VFE170 SOF tags while converting singleton outputs to output[0].'
elif number == 20:
    name = 'drivers/media/platform/qcom/camss/camss-vfe.c'
    subprocess.run(['git', '-C', str(tree), 'apply', '--exclude=' + name, str(patch)], check=True)
    path = tree / name
    text = path.read_text()
    for function in ['int vfe_queue_buffer_v2(', 'int vfe_flush_buffers(']:
        start = text.index(function)
        end = text.index('\n}\n', start) + 3
        body = text[start:end]
        old = '\tstruct vfe_line *line = container_of(vid, struct vfe_line, video_out);'
        assert body.count(old) == 1
        body = body.replace(old, '\tstruct vfe_output *output = container_of(vid, struct vfe_output, video_out);\n'
                                '\tstruct vfe_line *line = output->line;')
        assert body.count('\tstruct vfe_output *output;\n') == 1
        body = body.replace('\tstruct vfe_output *output;\n', '')
        assert body.count('\toutput = &line->output[0];\n\n') == 1
        body = body.replace('\toutput = &line->output[0];\n\n', '')
        text = text[:start] + body + text[end:]
    text = text.replace('].video_out', '].output[0].video_out')
    text = text.replace('l->video_out', 'l->output[0].video_out')
    path.write_text(text)
    note = 'Preserve maintained queue return/error and cleanup while moving video ownership from line to output.'
elif number == 38:
    text = patch.read_text()
    old = '-\tcase CAMSS_845:\n'
    assert text.count(old) == 1
    text = text.replace(old, old + '-\tcase CAMSS_8150:\n')
    rebased = patch.with_name('38-rebased.patch')
    rebased.write_text(text)
    subprocess.run(['git', '-C', str(tree), 'apply', '--recount', str(rebased)], check=True)
    note = 'Include maintained SM8150 case in common source-pad default dispatch, retaining its prior RAW mappings.'
elif number == 55:
    text = patch.read_text()
    old = ' \t\tsd->flags |= V4L2_SUBDEV_FL_HAS_DEVNODE;\n'
    assert text.count(old) == 1
    extra = (' \t\tif (vfe->camss->res->version == CAMSS_8150 &&\n'
             ' \t\t    vfe->res->hw_ops == &vfe_ops_170)\n'
             ' \t\t\tsd->flags |= V4L2_SUBDEV_FL_HAS_EVENTS;\n')
    text = text.replace(old, old + extra)
    rebased = patch.with_name('55-rebased.patch')
    rebased.write_text(text)
    subprocess.run(['git', '-C', str(tree), 'apply', '--recount', str(rebased)], check=True)
    note = 'Retain SM8150 VFE170 frame-sync event capability; use backend is_pix for pixel identity.'
elif number == 58:
    ioctl = 'drivers/media/v4l2-core/v4l2-ioctl.c'
    uapi = 'include/uapi/linux/videodev2.h'
    header = tree / 'include/uapi/linux/qcom-camss-config.h'
    if 'struct camss_stats_bhist {' not in header.read_text():
        subprocess.run(['git', '-C', str(tree), 'apply', '--exclude=' + ioctl,
                        '--exclude=' + uapi, str(patch)], check=True)
    else:
        digest = subprocess.check_output(['git', 'hash-object', str(header)], text=True).strip()
        assert digest.startswith('23c12b8955ef6')
    old = next(line + '\n' for line in (tree / ioctl).read_text().splitlines()
               if line.startswith('\tcase V4L2_META_FMT_MALI_C55_STATS:'))
    replace(ioctl, old, old + '\tcase V4L2_META_FMT_QCOM_ISP_STATS:\tdescr = "Qualcomm CAMSS ISP Statistics"; break;\n')
    old = "#define V4L2_META_FMT_MALI_C55_STATS\tv4l2_fourcc('C', '5', '5', 'S') /* ARM Mali-C55 3A Statistics */\n"
    replace(uapi, old, old + "\n/* Vendor specific - used for Qualcomm CAMSS ISP */\n"
            "#define V4L2_META_FMT_QCOM_ISP_STATS\tv4l2_fourcc('Q', 'C', 'I', 'S') /* Qualcomm CAMSS ISP Statistics */\n")
    note = 'Add QCIS metadata format while preserving all newer formats from current kernel.'
elif number == 64:
    text = patch.read_text()
    old = ' #include <media/v4l2-device.h>\n'
    assert text.count(old) == 1
    text = text.replace(old, old + ' #include <media/v4l2-event.h>\n')
    rebased = patch.with_name('64-rebased.patch')
    rebased.write_text(text)
    subprocess.run(['git', '-C', str(tree), 'apply', '--recount', str(rebased)], check=True)
    note = 'Preserve maintained frame-sync event header while adding ISP stats includes and nodes.'
elif number == 66:
    text = patch.read_text()
    text, count = re.subn(r'@@ -1487,6 \+1547,14 @@.*?(?=diff --git)', '', text, flags=re.S)
    assert count == 1
    rebased = patch.with_name('66-rebased.patch')
    rebased.write_text(text)
    subprocess.run(['git', '-C', str(tree), 'apply', str(rebased)], check=True)
    replace('drivers/media/platform/qcom/camss/camss-vfe.c',
            '\t/* gen1 shares this union; only the VFE170 path uses active_num. */\n'
            '\tif (vfe->res->hw_ops == &vfe_ops_170)\n\t\toutput->gen2.active_num = 0;',
            '\t/* Keep gen1 union state intact; every gen2 metadata output is reset. */\n'
            '\tif (!vfe->ops_gen1)\n\t\toutput->gen2.active_num = 0;')
    note = 'Keep stronger maintained buffer detachment/duplicate protection; reset active_num for every gen2 output, preserving gen1 union.'
elif number == 68:
    ioctl = 'drivers/media/v4l2-core/v4l2-ioctl.c'
    uapi = 'include/uapi/linux/videodev2.h'
    old = next(line + '\n' for line in (tree / ioctl).read_text().splitlines()
               if line.startswith('\tcase V4L2_META_FMT_QCOM_ISP_STATS:'))
    replace(ioctl, old, old + '\tcase V4L2_META_FMT_QCOM_ISP_PARAMS:\tdescr = "Qualcomm CAMSS ISP Parameters"; break;\n')
    old = next(line + '\n' for line in (tree / uapi).read_text().splitlines()
               if line.startswith('#define V4L2_META_FMT_QCOM_ISP_STATS'))
    replace(uapi, old, old + "#define V4L2_META_FMT_QCOM_ISP_PARAMS\tv4l2_fourcc('Q', 'C', 'I', 'P') /* Qualcomm CAMSS ISP Parameters */\n")
    note = 'Add QCIP metadata format adjacent to QCIS, preserving all newer upstream formats.'
elif number == 70:
    text = patch.read_text()
    old = ' \tstruct list_head queue;\n'
    assert text.count(old) == 1
    text = text.replace(old, old + ' \tbool sof_valid;\n')
    rebased = patch.with_name('70-rebased.patch')
    rebased.write_text(text)
    subprocess.run(['git', '-C', str(tree), 'apply', '--recount', str(rebased)], check=True)
    note = 'Retain maintained SOF validity in camss_buffer while adding a separate kernel parameters copy.'
else:
    raise SystemExit('No reviewed adaptation defined for this patch')
state['adapted'].append(number)
state.setdefault('adaptation_notes', {})[str(number)] = note
state.pop('first_conflict')
LOCK.write_text(json.dumps(state, indent=2) + '\n')
print('Rebased patch', number, note)
