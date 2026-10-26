"""Add a matched CAMIF backend without prematurely exposing an unfinished PIX line."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parent
TREE = Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
BASE = '7f81d76ee7e05c1713ca87b59fc31df806ae0295'
assert subprocess.check_output(['git', '-C', str(TREE), 'rev-parse', 'HEAD'], text=True).strip() == BASE
assert not subprocess.check_output(['git', '-C', str(TREE), 'status', '--porcelain'], text=True)
subprocess.run(['git', '-C', str(TREE), 'switch', '-c', 'samurai-vfe175-281'], check=True)
directory = TREE / 'drivers/media/platform/qcom/camss'


def replace(name, old, new, count=1):
    path = directory / name
    text = path.read_text()
    assert text.count(old) == count, (name, old, text.count(old))
    path.write_text(text.replace(old, new))


replace('Makefile', '\t\tcamss-vfe-17x.o \\\n', '\t\tcamss-vfe-17x.o \\\n\t\tcamss-vfe-175-camif.o \\\n')
replace('camss-vfe.h', 'void (*vfe_line_prepare)(struct vfe_line *line);',
        'int (*vfe_line_prepare)(struct vfe_line *line);')
replace('camss-vfe.h', 'extern const struct vfe_hw_ops vfe_ops_170;',
        'extern const struct vfe_hw_ops vfe_ops_170;\nextern const struct vfe_hw_ops vfe_ops_175;')
replace('camss-vfe.c', '\tif (ops->vfe_line_prepare)\n\t\tops->vfe_line_prepare(line);',
        '\tif (ops->vfe_line_prepare) {\n\t\tret = ops->vfe_line_prepare(line);\n\t\tif (ret)\n\t\t\tgoto error_enable_output;\n\t}')
replace('camss-vfe.c', 'vfe->res->hw_ops != &vfe_ops_170 ||',
        '(vfe->res->hw_ops != &vfe_ops_170 &&\n\t     vfe->res->hw_ops != &vfe_ops_175) ||')
replace('camss-vfe.c', 'vfe->res->hw_ops == &vfe_ops_170)',
        '(vfe->res->hw_ops == &vfe_ops_170 ||\n\t\t     vfe->res->hw_ops == &vfe_ops_175))')
replace('camss-vfe-780.c', 'static void vfe_line_prepare(struct vfe_line *line)',
        'static int vfe_line_prepare(struct vfe_line *line)')
replace('camss-vfe-780.c', '\t\tvfe_880_setup_pixel_pipe(to_vfe(line), pix->width, pix->height);\n}',
        '\t\tvfe_880_setup_pixel_pipe(to_vfe(line), pix->width, pix->height);\n\n\treturn 0;\n}')
replace('camss-vfe-17x.c', '#include "camss-vfe.h"', '#include "camss-vfe.h"\n#include "camss-vfe-175-camif.h"')
replace('camss-vfe-17x.c', '\tret = vfe_enable_output_v2(line);',
        '\tif (vfe->res->hw_ops->vfe_line_prepare) {\n\t\tret = vfe->res->hw_ops->vfe_line_prepare(line);\n\t\tif (ret)\n\t\t\tgoto error_enable_output;\n\t}\n\n\tret = vfe_enable_output_v2(line);')
path = directory / 'camss-vfe-17x.c'
text = path.read_text()
ops = text[text.index('const struct vfe_hw_ops vfe_ops_170 = {'):]
assert ops.endswith('};\n')
ops = ops.replace('vfe_ops_170 =', 'vfe_ops_175 =').replace('\t.global_reset =',
    '\t.vfe_line_prepare = vfe_175_camif_prepare,\n\t.global_reset =', 1)
path.write_text(text + '\n/* SM8150 full IFE: shared RDI transport, matched CAMIF preparation. */\n' + ops)
path = directory / 'camss.c'
text = path.read_text()
start = text.index('static const struct camss_subdev_resources vfe_res_8150[]')
end = text.index('static const ', start + 1)
section = text[start:end]
assert section.count('&vfe_ops_170') == 2 and section.count('.line_num = 3') == 2
path.write_text(text[:start] + section.replace('&vfe_ops_170', '&vfe_ops_175') + text[end:])

(directory / 'camss-vfe-175-camif.h').write_text('''/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef CAMSS_VFE_175_CAMIF_H
#define CAMSS_VFE_175_CAMIF_H

struct vfe_line;

int vfe_175_camif_prepare(struct vfe_line *line);

#endif /* CAMSS_VFE_175_CAMIF_H */
''')
(directory / 'camss-vfe-175-camif.c').write_text('''// SPDX-License-Identifier: GPL-2.0-only
/* Qualcomm SM8150 full VFE175 CAMIF pixel input configuration. */

#include <linux/bitfield.h>
#include <linux/io.h>
#include <linux/media-bus-format.h>

#include "camss.h"
#include "camss-vfe.h"
#include "camss-vfe-175-camif.h"

#define VFE_175_CORE_CFG                     0x050
#define VFE_175_CORE_PIXEL_PATTERN           GENMASK(2, 0)
#define VFE_175_CORE_DSP_ENABLE              BIT(3)
#define VFE_175_CORE_EXTERNAL_UPDATE         BIT(4)
#define VFE_175_CORE_INPUT_MUX               GENMASK(6, 5)
#define VFE_175_CORE_DSP_MODE                BIT(23)

#define VFE_175_CAMIF_CMD                    0x478
#define VFE_175_CAMIF_CLEAR_STATUS           BIT(2)
#define VFE_175_CAMIF_CONFIG                 0x47c
#define VFE_175_CAMIF_VFE_OUTPUT             BIT(6)
#define VFE_175_CAMIF_BUS_OUTPUT             BIT(7)
#define VFE_175_CAMIF_RAW_CROP               BIT(22)
#define VFE_175_CAMIF_LINE_SKIP              0x488
#define VFE_175_CAMIF_PIXEL_SKIP             0x48c
#define VFE_175_CAMIF_SKIP_PERIOD            0x490
#define VFE_175_CAMIF_IRQ_SUBSAMPLE           0x49c
#define VFE_175_CAMIF_EPOCH                  0x4a0
#define VFE_175_RAW_CROP_WIDTH               0xce4
#define VFE_175_RAW_CROP_HEIGHT              0xce8
#define VFE_175_RAW_CROP_LAST                GENMASK(13, 0)

/* The full IFE accepts decoded Bayer samples, not the packed RDI payload. */
static int vfe_175_bayer_pattern(u32 code)
{
\tswitch (code) {
\tcase MEDIA_BUS_FMT_SRGGB8_1X8:
\tcase MEDIA_BUS_FMT_SRGGB10_1X10:
\tcase MEDIA_BUS_FMT_SRGGB12_1X12:
\tcase MEDIA_BUS_FMT_SRGGB14_1X14:
\t\treturn 0;
\tcase MEDIA_BUS_FMT_SGRBG8_1X8:
\tcase MEDIA_BUS_FMT_SGRBG10_1X10:
\tcase MEDIA_BUS_FMT_SGRBG12_1X12:
\tcase MEDIA_BUS_FMT_SGRBG14_1X14:
\t\treturn 1;
\tcase MEDIA_BUS_FMT_SBGGR8_1X8:
\tcase MEDIA_BUS_FMT_SBGGR10_1X10:
\tcase MEDIA_BUS_FMT_SBGGR12_1X12:
\tcase MEDIA_BUS_FMT_SBGGR14_1X14:
\t\treturn 2;
\tcase MEDIA_BUS_FMT_SGBRG8_1X8:
\tcase MEDIA_BUS_FMT_SGBRG10_1X10:
\tcase MEDIA_BUS_FMT_SGBRG12_1X12:
\tcase MEDIA_BUS_FMT_SGBRG14_1X14:
\t\treturn 3;
\tdefault:
\t\treturn -EINVAL;
\t}
}

int vfe_175_camif_prepare(struct vfe_line *line)
{
\tstruct vfe_device *vfe = to_vfe(line);
\tconst struct v4l2_mbus_framefmt *input = &line->fmt[MSM_VFE_PAD_SINK];
\tu32 core, last_pixel, last_line;
\tint pattern;

\t/* RDI register programming remains entirely in the shared 17x backend. */
\tif (!line->is_pix)
\t\treturn 0;
\tif (vfe->res->is_lite || vfe->camss->res->version != CAMSS_8150)
\t\treturn -EINVAL;

\tpattern = vfe_175_bayer_pattern(input->code);
\tif (pattern < 0)
\t\treturn pattern;
\tif (!input->width || !input->height ||
\t    input->width - 1 > FIELD_MAX(VFE_175_RAW_CROP_LAST) ||
\t    input->height - 1 > FIELD_MAX(VFE_175_RAW_CROP_LAST))
\t\treturn -EINVAL;

\tlast_pixel = input->width - 1;
\tlast_line = input->height - 1;

\t/* Single-IFE CSID input; preserve core fields owned by other paths. */
\tcore = readl_relaxed(vfe->base + VFE_175_CORE_CFG);
\tcore &= ~(VFE_175_CORE_PIXEL_PATTERN | VFE_175_CORE_DSP_ENABLE |
\t\t  VFE_175_CORE_EXTERNAL_UPDATE | VFE_175_CORE_INPUT_MUX |
\t\t  VFE_175_CORE_DSP_MODE);
\tcore |= FIELD_PREP(VFE_175_CORE_PIXEL_PATTERN, pattern);
\twritel_relaxed(core, vfe->base + VFE_175_CORE_CFG);

\twritel_relaxed(VFE_175_CAMIF_CLEAR_STATUS,
\t\t       vfe->base + VFE_175_CAMIF_CMD);
\twritel_relaxed(VFE_175_CAMIF_VFE_OUTPUT | VFE_175_CAMIF_BUS_OUTPUT |
\t\t       VFE_175_CAMIF_RAW_CROP, vfe->base + VFE_175_CAMIF_CONFIG);

\t/* Sixteen accepted lines/pixels, no dropped frames or IRQ subsampling. */
\twritel_relaxed(0xffff, vfe->base + VFE_175_CAMIF_LINE_SKIP);
\twritel_relaxed(0xffff, vfe->base + VFE_175_CAMIF_PIXEL_SKIP);
\twritel_relaxed(0x0f0f, vfe->base + VFE_175_CAMIF_SKIP_PERIOD);
\twritel_relaxed(1, vfe->base + VFE_175_CAMIF_IRQ_SUBSAMPLE);

\t/* Full decoded frame; output crop/scaling belongs to the pixel modules. */
\twritel_relaxed(last_pixel, vfe->base + VFE_175_RAW_CROP_WIDTH);
\twritel_relaxed(last_line, vfe->base + VFE_175_RAW_CROP_HEIGHT);
\twritel_relaxed((last_line / 2) << 16 | min_t(u32, last_line, 20),
\t\t       vfe->base + VFE_175_CAMIF_EPOCH);

\t/* The caller must arm processing/outputs before issuing PIX reg update. */
\treturn 0;
}
''')
subprocess.run(['git', '-C', str(TREE), 'diff', '--check'], check=True)
files = ['Makefile', 'camss.c', 'camss-vfe.h', 'camss-vfe.c', 'camss-vfe-17x.c',
         'camss-vfe-780.c', 'camss-vfe-175-camif.c', 'camss-vfe-175-camif.h']
report = dict(stage=281, base=BASE, branch='samurai-vfe175-281',
              files={name: hashlib.sha256((directory / name).read_bytes()).hexdigest() for name in files},
              full_sm8150_resources_matched=2, line_count_still_three=True,
              pix_line_not_exposed=True, no_phone_changes=True)
(ROOT / 'camif-source-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
