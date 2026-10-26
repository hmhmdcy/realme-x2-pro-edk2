from pathlib import Path
import difflib
import hashlib
import json
import re

root = Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel145')
out = Path('/mnt/e/edk2-samurai-out/kernel145')
out.mkdir(mode=0o700, exist_ok=True)
before = (root / 'drivers/gpu/drm/msm/dsi/dsi_host.c').read_text()
assert not (out / 'dsi-host-before-private.c').exists()
assert not (root / 'drivers/gpu/drm/msm/msm_dsi_trace.h').exists()
(out / 'dsi-host-before-private.c').write_text(before)
text = before.replace('#include "phy/dsi_phy.h"', '#include "phy/dsi_phy.h"\n\n#define CREATE_TRACE_POINTS\n#include "msm_dsi_trace.h"\n#undef CREATE_TRACE_POINTS')
assert text != before

def function_range(source, name):
    match = re.search(r'^static[^;{}]*\b' + name + r'\([^;{}]*\)\n\{', source, re.M)
    assert match, name
    depth = 1
    end = match.end()
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return match.start(), end

helpers = [('dsi_clk_status', 'REG_DSI_CLK_STATUS'),
           ('dsi_fifo_status', 'REG_DSI_FIFO_STATUS'),
           ('dsi_ack_err_status', 'REG_DSI_ACK_ERR_STATUS'),
           ('dsi_timeout_status', 'REG_DSI_TIMEOUT_STATUS'),
           ('dsi_status', 'REG_DSI_STATUS0'),
           ('dsi_dln0_phy_err', 'REG_DSI_DLN0_PHY_ERR')]
for name, reg in helpers:
    start, end = function_range(text, name)
    body = text[start:end]
    assert body.count('dsi_read(') == 1
    body = body[:-2] + '\n\n\ttrace_msm_dsi_error_status(msm_host->id, ' + reg + ',\n\t\t\t\t   status, msm_host->err_work_state);\n}'
    text = text[:start] + body + text[end:]

start, end = function_range(text, 'dsi_err_worker')
body = text[start:end]
body = body.replace('\tpr_err_ratelimited(', '\ttrace_msm_dsi_error_work(msm_host->id, status, false);\n\tpr_err_ratelimited(', 1)
body = body.replace('\tdsi_intr_ctrl(msm_host, DSI_IRQ_MASK_ERROR, 1);', '\tdsi_intr_ctrl(msm_host, DSI_IRQ_MASK_ERROR, 1);\n\ttrace_msm_dsi_error_work(msm_host->id, status, true);', 1)
text = text[:start] + body + text[end:]
needle = '\tif (isr & DSI_IRQ_ERROR)\n\t\tdsi_error(msm_host);'
assert text.count(needle) == 1
text = text.replace(needle, '\tif (isr & DSI_IRQ_ERROR) {\n\t\ttrace_msm_dsi_error_irq(msm_host->id, isr);\n\t\tdsi_error(msm_host);\n\t}')
header = '''/* SPDX-License-Identifier: GPL-2.0-only */
#undef TRACE_SYSTEM
#define TRACE_SYSTEM drm_msm_dsi

#if !defined(_MSM_DSI_TRACE_H_) || defined(TRACE_HEADER_MULTI_READ)
#define _MSM_DSI_TRACE_H_

#include <linux/tracepoint.h>

TRACE_EVENT(msm_dsi_error_irq,
	TP_PROTO(int id, u32 isr),
	TP_ARGS(id, isr),
	TP_STRUCT__entry(
		__field(int, id)
		__field(u32, isr)
	),
	TP_fast_assign(
		__entry->id = id;
		__entry->isr = isr;
	),
	TP_printk("id=%d isr=0x%x", __entry->id, __entry->isr)
);

TRACE_EVENT(msm_dsi_error_status,
	TP_PROTO(int id, u32 reg, u32 raw, u32 state),
	TP_ARGS(id, reg, raw, state),
	TP_STRUCT__entry(
		__field(int, id)
		__field(u32, reg)
		__field(u32, raw)
		__field(u32, state)
	),
	TP_fast_assign(
		__entry->id = id;
		__entry->reg = reg;
		__entry->raw = raw;
		__entry->state = state;
	),
	TP_printk("id=%d reg=0x%x raw=0x%x state=0x%x", __entry->id,
		  __entry->reg, __entry->raw, __entry->state)
);

TRACE_EVENT(msm_dsi_error_work,
	TP_PROTO(int id, u32 state, bool done),
	TP_ARGS(id, state, done),
	TP_STRUCT__entry(
		__field(int, id)
		__field(u32, state)
		__field(bool, done)
	),
	TP_fast_assign(
		__entry->id = id;
		__entry->state = state;
		__entry->done = done;
	),
	TP_printk("id=%d state=0x%x done=%d", __entry->id,
		  __entry->state, __entry->done)
);

#endif /* _MSM_DSI_TRACE_H_ */

#undef TRACE_INCLUDE_PATH
#define TRACE_INCLUDE_PATH ../../drivers/gpu/drm/msm
#undef TRACE_INCLUDE_FILE
#define TRACE_INCLUDE_FILE msm_dsi_trace
#include <trace/define_trace.h>
'''
(out / 'dsi-host-candidate-private.c').write_text(text)
(ref / 'msm_dsi_trace.h').write_text(header)
patch = ''.join(difflib.unified_diff(before.splitlines(True), text.splitlines(True),
                                   fromfile='a/drivers/gpu/drm/msm/dsi/dsi_host.c',
                                   tofile='b/drivers/gpu/drm/msm/dsi/dsi_host.c'))
patch += ''.join(difflib.unified_diff([], header.splitlines(True), fromfile='/dev/null',
                                    tofile='b/drivers/gpu/drm/msm/msm_dsi_trace.h'))
(ref / 'dsi-observation.patch').write_text(patch)
report = dict(stage=145, baseline_source_stage=144, candidate_prepared_offline=True,
              build_tree_modified=False, existing_mmio_values_only=True,
              no_printk_or_register_access_added=True, default_disabled_tracepoints=True,
              baseline_source_sha256=hashlib.sha256(before.encode()).hexdigest(),
              candidate_source_sha256=hashlib.sha256(text.encode()).hexdigest(),
              trace_header_sha256=hashlib.sha256(header.encode()).hexdigest(),
              actual_functions_tested=False, built=False, deployed=False,
              display_accepted=False, gpu_accepted=False, charging_accepted=False,
              goal_complete=False)
(ref / 'source-preparation-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print('K145_DSI_RAW_STATUS_AND_RECOVERY_OBSERVATION_PREPARED_OFFLINE')
