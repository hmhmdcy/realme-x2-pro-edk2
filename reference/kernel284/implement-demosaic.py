"""Add the matched VFE175 Demosaic36 backend after the WB full build terminates."""
from pathlib import Path
import json
import subprocess

ROOT=Path(__file__).resolve().parent
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel284')
TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
SOURCE=TREE/'drivers/media/platform/qcom/camss'
BASE='97a4c563803fd943e5a4c3f0359548a3d758bcc5'
git=lambda *a:subprocess.check_output(['git','-C',str(TREE),*a],text=True).strip()
report=json.loads((ROOT/'wb-full-build-validation.json').read_text())
assert report['terminal'] and report['commit']==BASE and report['actual_ko_files_all_hashed']
assert git('rev-parse','HEAD')==BASE and not git('status','--porcelain')
assert subprocess.run(['git','-C',str(TREE),'show-ref','--verify','--quiet','refs/heads/samurai-vfe175-demosaic284']).returncode==1
subprocess.run(['git','-C',str(TREE),'switch','-c','samurai-vfe175-demosaic284'],check=True,capture_output=True)
(SOURCE/'camss-vfe-175-demosaic.h').write_text('''/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef CAMSS_VFE_175_DEMOSAIC_H
#define CAMSS_VFE_175_DEMOSAIC_H

#include <linux/types.h>

struct vfe_device;
struct vfe_line;

struct vfe_175_demosaic_config {
	u16 lambda_g;
	u16 lambda_rb;
	u16 classifier_a;
	s16 classifier_w;
	bool directional_g_disable;
	bool directional_rb_disable;
	bool cosited_rgb;
	bool dynamic_g_clamp;
	bool dynamic_rb_clamp;
	bool enabled;
};

int vfe_175_demosaic_configure(struct vfe_device *vfe,
			       const struct vfe_175_demosaic_config *config);
int vfe_175_demosaic_prepare(struct vfe_line *line);
void vfe_175_demosaic_stop(struct vfe_device *vfe);

#endif /* CAMSS_VFE_175_DEMOSAIC_H */
''')
(SOURCE/'camss-vfe-175-demosaic.c').write_text('''// SPDX-License-Identifier: GPL-2.0-only
/* SM8150 full VFE175 uses Demosaic36, selected by the platform mask. */

#include <linux/bitfield.h>
#include <linux/io.h>

#include "camss.h"
#include "camss-vfe.h"
#include "camss-vfe-175-demosaic.h"

#define VFE_175_LENS_ENABLE		0x040
#define VFE_175_LENS_DEMOSAIC		BIT(10)
#define VFE_175_DEMO_CONFIG		0x6f8
#define VFE_175_DEMO_DIR_G_DISABLE	BIT(0)
#define VFE_175_DEMO_DIR_RB_DISABLE	BIT(1)
#define VFE_175_DEMO_COSITED		BIT(4)
#define VFE_175_DEMO_DYNAMIC_G		BIT(8)
#define VFE_175_DEMO_DYNAMIC_RB		BIT(9)
#define VFE_175_DEMO_LINE_BUFFER_ONLY	BIT(11)
#define VFE_175_DEMO_CONFIG_FIELDS	(VFE_175_DEMO_DIR_G_DISABLE | \\
	VFE_175_DEMO_DIR_RB_DISABLE | VFE_175_DEMO_COSITED | \\
	VFE_175_DEMO_DYNAMIC_G | VFE_175_DEMO_DYNAMIC_RB | \\
	VFE_175_DEMO_LINE_BUFFER_ONLY)
#define VFE_175_DEMO_INTERPOLATION	0x71c
#define VFE_175_DEMO_LAMBDA_G		GENMASK(15, 8)
#define VFE_175_DEMO_LAMBDA_RB		GENMASK(31, 24)
#define VFE_175_DEMO_CLASSIFIER		0x720
#define VFE_175_DEMO_CLASSIFIER_W		GENMASK(9, 0)
#define VFE_175_DEMO_CLASSIFIER_A		GENMASK(31, 20)

static bool vfe_175_demosaic_supported(struct vfe_device *vfe)
{
	return !vfe->res->is_lite && vfe->camss->res->version == CAMSS_8150;
}

int vfe_175_demosaic_configure(struct vfe_device *vfe,
			       const struct vfe_175_demosaic_config *config)
{
	u32 value, mode = 0;

	/* The matched Demosaic36 tuning contract bounds A to 400 and W to s10. */
	if (!vfe_175_demosaic_supported(vfe) || !config ||
	    config->lambda_g > 255 || config->lambda_rb > 255 ||
	    config->classifier_a > 400 || config->classifier_w < -512 ||
	    config->classifier_w > 511)
		return -EINVAL;

	if (config->directional_g_disable)
		mode |= VFE_175_DEMO_DIR_G_DISABLE;
	if (config->directional_rb_disable)
		mode |= VFE_175_DEMO_DIR_RB_DISABLE;
	if (config->cosited_rgb)
		mode |= VFE_175_DEMO_COSITED;
	if (config->dynamic_g_clamp)
		mode |= VFE_175_DEMO_DYNAMIC_G;
	if (config->dynamic_rb_clamp)
		mode |= VFE_175_DEMO_DYNAMIC_RB;
	if (!config->enabled)
		mode |= VFE_175_DEMO_LINE_BUFFER_ONLY;

	value = readl_relaxed(vfe->base + VFE_175_DEMO_CONFIG);
	value &= ~VFE_175_DEMO_CONFIG_FIELDS;
	writel_relaxed(value | mode, vfe->base + VFE_175_DEMO_CONFIG);
	value = readl_relaxed(vfe->base + VFE_175_DEMO_INTERPOLATION);
	value &= ~(VFE_175_DEMO_LAMBDA_G | VFE_175_DEMO_LAMBDA_RB);
	value |= FIELD_PREP(VFE_175_DEMO_LAMBDA_G, config->lambda_g) |
		 FIELD_PREP(VFE_175_DEMO_LAMBDA_RB, config->lambda_rb);
	writel_relaxed(value, vfe->base + VFE_175_DEMO_INTERPOLATION);
	value = readl_relaxed(vfe->base + VFE_175_DEMO_CLASSIFIER);
	value &= ~(VFE_175_DEMO_CLASSIFIER_W | VFE_175_DEMO_CLASSIFIER_A);
	value |= FIELD_PREP(VFE_175_DEMO_CLASSIFIER_W,
			    (u32)config->classifier_w & 0x3ff) |
		 FIELD_PREP(VFE_175_DEMO_CLASSIFIER_A, config->classifier_a);
	writel_relaxed(value, vfe->base + VFE_175_DEMO_CLASSIFIER);

	/* Publish the configuration before enabling the module; no PIX RUP yet. */
	wmb();
	value = readl_relaxed(vfe->base + VFE_175_LENS_ENABLE);
	value &= ~VFE_175_LENS_DEMOSAIC;
	if (config->enabled)
		value |= VFE_175_LENS_DEMOSAIC;
	writel_relaxed(value, vfe->base + VFE_175_LENS_ENABLE);

	return 0;
}

int vfe_175_demosaic_prepare(struct vfe_line *line)
{
	/* Hardware bring-up profile, not a calibrated sensor or scene tuning. */
	const struct vfe_175_demosaic_config config = {
		.lambda_g = 128,
		.lambda_rb = 0,
		.classifier_a = 128,
		.classifier_w = 102,
		.dynamic_g_clamp = true,
		.enabled = true,
	};

	if (!line->is_pix)
		return 0;

	return vfe_175_demosaic_configure(to_vfe(line), &config);
}

void vfe_175_demosaic_stop(struct vfe_device *vfe)
{
	u32 value;

	if (!vfe_175_demosaic_supported(vfe))
		return;
	value = readl_relaxed(vfe->base + VFE_175_LENS_ENABLE);
	writel_relaxed(value & ~VFE_175_LENS_DEMOSAIC,
		       vfe->base + VFE_175_LENS_ENABLE);
}
''')

def replace(name,old,new):
    f=SOURCE/name;s=f.read_text();assert s.count(old)==1,(name,old);f.write_text(s.replace(old,new))
replace('Makefile','\t\tcamss-vfe-175-pixel.o \\\n','\t\tcamss-vfe-175-pixel.o \\\n\t\tcamss-vfe-175-demosaic.o \\\n')
replace('camss-vfe-175-pixel.h','void vfe_175_pixel_prepare(struct vfe_line *line);','int vfe_175_pixel_prepare(struct vfe_line *line);\nvoid vfe_175_pixel_stop(struct vfe_device *vfe);')
replace('camss-vfe-175-pixel.c','#include "camss-vfe-175-pixel.h"','#include "camss-vfe-175-pixel.h"\n#include "camss-vfe-175-demosaic.h"')
replace('camss-vfe-175-pixel.c','void vfe_175_pixel_prepare(struct vfe_line *line)','int vfe_175_pixel_prepare(struct vfe_line *line)')
replace('camss-vfe-175-pixel.c','\tif (!line->is_pix)\n\t\treturn;\n\t/* Reopening','\tint ret;\n\n\tif (!line->is_pix)\n\t\treturn 0;\n\tret = vfe_175_demosaic_prepare(line);\n\tif (ret)\n\t\treturn ret;\n\t/* Reopening')
replace('camss-vfe-175-pixel.c','\tvfe_175_wb_write(vfe);\n}\n\nvoid vfe_175_params_apply','\tvfe_175_wb_write(vfe);\n\n\treturn 0;\n}\n\nvoid vfe_175_pixel_stop(struct vfe_device *vfe)\n{\n\tvfe_175_demosaic_stop(vfe);\n}\n\nvoid vfe_175_params_apply')
replace('camss-vfe-17x.c','\tvfe_175_pixel_prepare(line);\n\n\treturn 0;','\treturn vfe_175_pixel_prepare(line);')
replace('camss-vfe-17x.c','error_enable_output:\n\tvfe_put_output(line);','error_enable_output:\n\tif (line->is_pix)\n\t\tvfe_175_pixel_stop(vfe);\n\tvfe_put_output(line);')
replace('camss-vfe-17x.c','\tif (output->line->is_pix)\n\t\tvfe_175_full_stop(vfe, output);\n\telse', '\tif (output->line->is_pix) {\n\t\tvfe_175_full_stop(vfe, output);\n\t\tif (output->pad == MSM_VFE_PAD_SRC)\n\t\t\tvfe_175_pixel_stop(vfe);\n\t} else')
print(git('diff','--stat'))
