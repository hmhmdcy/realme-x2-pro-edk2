"""Prepare a fresh145 archive verifier with DSI events retained for correlation."""
from pathlib import Path
import ast

root = Path('/mnt/e/RealmeX2Pro edk2')
target = root / 'reference/kernel145/verify-startup-irq-idle.py'
assert not target.exists()
text = (root / 'reference/kernel143/verify-startup-irq-idle.py').read_text().replace('143', '145')
before = "if name.startswith('dpu_') or name.startswith('msm_gpu_') or name.startswith('msm_atomic_'):"
assert before in text
text = text.replace(before, "if name.startswith('dpu_') or name.startswith('msm_gpu_') or name.startswith('msm_atomic_') or name.startswith('msm_dsi_'):")
before = "(ref / 'startup-irq-idle-validation.json').write_text"
assert before in text
text = text.replace(before, "enabled = set(json.loads(small['enabled-events.json']))\nexpected_dsi = {'events/drm_msm_dsi/' + name + '/enable' for name in ['msm_dsi_error_irq', 'msm_dsi_error_status', 'msm_dsi_error_work']}\nassert expected_dsi <= enabled\nreport.update(three_new_dsi_tracepoints_enabled=True, raw_dsi_events_retained_private=True, dsi_event_counts={name:counter[name] for name in ['msm_dsi_error_irq', 'msm_dsi_error_status', 'msm_dsi_error_work']})\n" + before)
ast.parse(text)
target.write_text(text)
print('K145_NEW_DSI_ARCHIVE_VERIFIER_PREPARED_NOT_EXECUTED')
