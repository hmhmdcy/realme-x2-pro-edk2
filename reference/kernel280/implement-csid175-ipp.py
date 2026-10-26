"""Implement gen2 IPP transport from the matched OEM175 register contract.

The VFE175 image processor/output backend is still required before a PIX
consumer can link. Board DT and userspace are not modified here.
"""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parent
TREE = Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
PREFIX = 'drivers/media/platform/qcom/camss/'
BASE = '30b0daa8cab27f64be4f058629b65f8af1a7cc6f'
git = lambda *args: subprocess.check_output(['git', '-C', str(TREE), *args], text=True)
assert git('rev-parse', 'HEAD').strip() == BASE and not git('status', '--porcelain')
assert git('branch', '--show-current').strip() == 'samurai-ipp175-280'
changes = []


def update(name, transform):
    path = TREE / PREFIX / name
    old = path.read_text()
    new = transform(old)
    assert new != old, name
    changes.append(dict(path=PREFIX+name, before_sha256=hashlib.sha256(old.encode()).hexdigest(),
                        after_sha256=hashlib.sha256(new.encode()).hexdigest()))
    path.write_text(new)


def replace_once(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new)


# Return transport errors to s_stream, including an IPP halt timeout.
for name, function in [('camss-csid-340.c', 'csid_configure_streams'),
                       ('camss-csid-4-1.c', 'csid_configure_stream'),
                       ('camss-csid-4-7.c', 'csid_configure_stream'),
                       ('camss-csid-680.c', 'csid_configure_stream'),
                       ('camss-csid-gen3.c', 'csid_configure_stream')]:
    def convert(text, function=function):
        start = text.index('static void ' + function + '(')
        end = text.index('\n}\n', start)
        body = text[start:end]
        body = body.replace('static void ' + function, 'static int ' + function, 1)
        body = body.replace('return;', 'return 0;')
        return text[:start] + body + '\n\n\treturn 0;' + text[end:]
    update(name, convert)


def header(text):
    text = replace_once(text, 'void (*configure_stream)(struct csid_device *csid, u8 enable);',
                        'int (*configure_stream)(struct csid_device *csid, u8 enable);')
    text = replace_once(text, 'struct csid_subdev_resources {\n\tbool is_lite;',
                        'struct csid_subdev_resources {\n\tbool is_lite;\n'
                        '\tbool has_ipp; /* gen2 pixel input path, separate from RDI3 */')
    return text
update('camss-csid.h', header)


def core(text):
    text = replace_once(text, '\tcsid->res->hw_ops->configure_stream(csid, enable);\n\n\treturn 0;',
                        '\treturn csid->res->hw_ops->configure_stream(csid, enable);')
    old = '\t\tstruct device *dev = csid->camss->dev;\n\n\t\tif (flags & MEDIA_LNK_FL_ENABLED)'
    new = '''\t\tstruct device *dev = csid->camss->dev;

		/* Gen2 full CSIDs have three RDIs and a distinct pixel path. */
		if (csid->res->has_ipp && (flags & MEDIA_LNK_FL_ENABLED)) {
			struct vfe_line *line;
			bool ipp = !csid_is_lite(csid) &&
				   local->index == MSM_CSID_PAD_FIRST_SRC + 3;

			if (!is_media_entity_v4l2_subdev(remote->entity))
				return -EINVAL;
			line = v4l2_get_subdevdata(media_entity_to_v4l2_subdev(remote->entity));
			if (ipp != line->is_pix)
				return -EINVAL;
		}

		if (flags & MEDIA_LNK_FL_ENABLED)'''
    return replace_once(text, old, new)
update('camss-csid.c', core)


def resources(text):
    start = text.index('static const struct camss_subdev_resources csid_res_8150[]')
    end = text.index('\n};', start)
    block = text[start:end]
    assert block.count('.hw_ops = &csid_ops_gen2,') == 2
    block = block.replace('.hw_ops = &csid_ops_gen2,', '.has_ipp = true,\n\t\t\t.hw_ops = &csid_ops_gen2,')
    return text[:start] + block + text[end:]
update('camss.c', resources)

registers = '''/* CSID175 full IPP, verified against the SM8150 OEM descriptor. */
#define CSID_IPP_IRQ_STATUS		0x30
#define CSID_IPP_IRQ_MASK		0x34
#define CSID_IPP_IRQ_CLEAR		0x38
#define CSID_IPP_CFG0			0x200
#define	IPP_CFG0_FORMAT_MEASURE_EN	BIT(0)
#define	IPP_CFG0_TIMESTAMP_EN		BIT(1)
#define	IPP_CFG0_PIXEL_STORE_EN		BIT(7)
#define	IPP_CFG0_DECODE_FORMAT		12
#define	IPP_CFG0_DATA_TYPE		16
#define	IPP_CFG0_VIRTUAL_CHANNEL		22
#define	IPP_CFG0_ENABLE			BIT(31)
#define CSID_IPP_CFG1			0x204
#define CSID_IPP_CTRL			0x208
#define CSID_IPP_FRM_DROP_PATTERN		0x20c
#define CSID_IPP_FRM_DROP_PERIOD		0x210
#define CSID_IPP_IRQ_SUBSAMPLE_PATTERN	0x214
#define CSID_IPP_IRQ_SUBSAMPLE_PERIOD	0x218
#define CSID_IPP_PIX_DROP_PATTERN		0x224
#define CSID_IPP_PIX_DROP_PERIOD		0x228
#define CSID_IPP_LINE_DROP_PATTERN	0x22c
#define CSID_IPP_LINE_DROP_PERIOD		0x230
#define CSID_IPP_STATUS			0x254
#define	IPP_STATUS_HALTED		BIT(0)
#define	IPP_IRQ_FIFO_OVERFLOW		BIT(2)
#define CSID_GEN2_IPP_PORT		3

'''
helpers = '''static bool csid_gen2_port_is_ipp(struct csid_device *csid, u8 port)
{
	return csid->res->has_ipp && !csid_is_lite(csid) &&
	       port == CSID_GEN2_IPP_PORT;
}

static int csid_gen2_validate_ipp(struct csid_device *csid, u8 port, u8 vc)
{
	const struct v4l2_mbus_framefmt *input;
	const struct csid_format_info *format;

	if (!csid_gen2_port_is_ipp(csid, port) || vc > 31)
		return -EINVAL;
	input = &csid->fmt[MSM_CSID_PAD_FIRST_SRC + port];
	format = csid_get_fmt_entry(csid->res->formats->formats,
				    csid->res->formats->nformats, input->code);
	/* RAW6..RAW16: unpack pixels, never feed payload-only bytes to PIX. */
	if (format->code != input->code || format->data_type < 0x28 ||
	    format->data_type > 0x2e ||
	    format->decode_format == DECODE_FORMAT_PAYLOAD_ONLY)
		return -EINVAL;

	return 0;
}

static int csid_gen2_configure_ipp(struct csid_device *csid, u8 port, u8 vc)
{
	const struct v4l2_mbus_framefmt *input;
	const struct csid_format_info *format;
	u32 value;
	int ret;

	ret = csid_gen2_validate_ipp(csid, port, vc);
	if (ret)
		return ret;

	input = &csid->fmt[MSM_CSID_PAD_FIRST_SRC + port];
	format = csid_get_fmt_entry(csid->res->formats->formats,
				    csid->res->formats->nformats, input->code);
	writel(0, csid->base + CSID_IPP_CTRL);
	writel(0, csid->base + CSID_IPP_IRQ_MASK);
	writel(0x7fff, csid->base + CSID_IPP_IRQ_CLEAR);
	writel(1, csid->base + CSID_IRQ_CMD);

	value = IPP_CFG0_FORMAT_MEASURE_EN | IPP_CFG0_TIMESTAMP_EN |
		IPP_CFG0_PIXEL_STORE_EN |
		format->decode_format << IPP_CFG0_DECODE_FORMAT |
		format->data_type << IPP_CFG0_DATA_TYPE |
		vc << IPP_CFG0_VIRTUAL_CHANNEL;
	/* The IPP has CID slot zero; port 3 does not mean DT_ID 3. */
	writel(value, csid->base + CSID_IPP_CFG0);
	writel(2, csid->base + CSID_IPP_CFG1);
	writel(1, csid->base + CSID_IPP_FRM_DROP_PERIOD);
	writel(0, csid->base + CSID_IPP_FRM_DROP_PATTERN);
	writel(1, csid->base + CSID_IPP_IRQ_SUBSAMPLE_PERIOD);
	writel(0, csid->base + CSID_IPP_IRQ_SUBSAMPLE_PATTERN);
	writel(1, csid->base + CSID_IPP_PIX_DROP_PERIOD);
	writel(0, csid->base + CSID_IPP_PIX_DROP_PATTERN);
	writel(1, csid->base + CSID_IPP_LINE_DROP_PERIOD);
	writel(0, csid->base + CSID_IPP_LINE_DROP_PATTERN);
	writel(value | IPP_CFG0_ENABLE, csid->base + CSID_IPP_CFG0);
	writel(IPP_IRQ_FIFO_OVERFLOW, csid->base + CSID_IPP_IRQ_MASK);

	return 0;
}

static int csid_gen2_stop_ipp(struct csid_device *csid)
{
	u32 value;
	int ret;

	if (!(readl(csid->base + CSID_IPP_CFG0) & IPP_CFG0_ENABLE))
		return 0;

	writel(0, csid->base + CSID_IPP_IRQ_MASK);
	/* Internal halt at a frame boundary, then wait for the real status. */
	writel(0, csid->base + CSID_IPP_CTRL);
	ret = readl_poll_timeout(csid->base + CSID_IPP_STATUS, value,
				 value & IPP_STATUS_HALTED, 10,
				 CSID_RESET_TIMEOUT_MS * 1000);
	if (ret)
		return ret;

	value = readl(csid->base + CSID_IPP_CFG0);
	writel(value & ~IPP_CFG0_ENABLE, csid->base + CSID_IPP_CFG0);

	return 0;
}

'''
configure = '''static int csid_configure_stream(struct csid_device *csid, u8 enable)
{
	struct csid_testgen_config *tg = &csid->testgen;
	int ret;
	u8 i, first = MSM_CSID_MAX_SRC_STREAMS;

	if (enable && csid_gen2_port_is_ipp(csid, CSID_GEN2_IPP_PORT) &&
	    csid->phy.en_vc & BIT(CSID_GEN2_IPP_PORT)) {
		ret = csid_gen2_validate_ipp(csid, CSID_GEN2_IPP_PORT, 0);
		if (ret)
			return ret;
	}

	for (i = 0; i < MSM_CSID_MAX_SRC_STREAMS; i++) {
		if (!(csid->phy.en_vc & BIT(i)))
			continue;

		if (first == MSM_CSID_MAX_SRC_STREAMS)
			first = i;

		if (csid_gen2_port_is_ipp(csid, i)) {
			if (!enable) {
				ret = csid_gen2_stop_ipp(csid);
				if (ret)
					return ret;
				continue;
			}
			ret = csid_gen2_configure_ipp(csid, i, 0);
			if (ret)
				return ret;
			__csid_configure_rx(csid, &csid->phy, 0);
			writel(1, csid->base + CSID_IPP_CTRL);
		} else {
			__csid_configure_rdi_stream(csid, enable, i, 0);
			__csid_configure_rx(csid, &csid->phy, 0);
			__csid_ctrl_rdi(csid, enable, i);
		}
	}

	/* Start the source after paths are armed; stop it after paths halt. */
	if (tg->enabled && first < MSM_CSID_MAX_SRC_STREAMS)
		__csid_configure_testgen(csid, enable, first, 0);

	return 0;
}
'''


def gen2(text):
    text = replace_once(text, '#include <linux/io.h>\n', '#include <linux/io.h>\n#include <linux/iopoll.h>\n')
    text = replace_once(text, 'val |=  enable << RDI_CFG0_ENABLE;', 'val |= (u32)enable << RDI_CFG0_ENABLE;')
    text = replace_once(text, '#define CSID_TPG_CTRL', registers + '#define CSID_TPG_CTRL')
    start = text.index('static void csid_configure_stream(')
    end = text.index('\n}\n', start) + 3
    text = text[:start] + helpers + configure + text[end:]
    old = '\t\t\tval = readl_relaxed(csid->base + CSID_CSI2_RDIN_IRQ_STATUS(i));\n\t\t\twritel_relaxed(val, csid->base + CSID_CSI2_RDIN_IRQ_CLEAR(i));'
    new = '''\t\t\tif (csid_gen2_port_is_ipp(csid, i)) {
				val = readl_relaxed(csid->base + CSID_IPP_IRQ_STATUS);
				writel_relaxed(val, csid->base + CSID_IPP_IRQ_CLEAR);
				if (val & IPP_IRQ_FIFO_OVERFLOW)
					dev_err_ratelimited(csid->camss->dev,
							    "CSID%u IPP FIFO overflow\\n", csid->id);
			} else {
				val = readl_relaxed(csid->base + CSID_CSI2_RDIN_IRQ_STATUS(i));
				writel_relaxed(val, csid->base + CSID_CSI2_RDIN_IRQ_CLEAR(i));
			}'''
    return replace_once(text, old, new)
update('camss-csid-gen2.c', gen2)

subprocess.run(['git', '-C', str(TREE), 'diff', '--check'], check=True)
(ROOT / 'csid175-source-validation.json').write_text(json.dumps(dict(stage=280, base_commit=BASE,
    changes=changes, source_ipp_implemented=True, vfe175_pixel_backend_not_implemented=True,
    only_sm8150_resources_enable_gen2_ipp=True, board_dt_unchanged=True,
    candidate_not_deployed=True), indent=2) + '\n')
print('Implemented IPP transport, halt/error propagation, IRQ handling and graph gate in', len(changes), 'files')
