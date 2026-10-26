"""Record the demonstrated neutral-patch failure separately from transport success."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parent
p=ROOT/'raw-nv12-tpg-comparison.json';d=json.loads(p.read_text())
white=d['patches'][0];black=d['patches'][7]
assert all(v==1020 for v in white['raw_cfa_means'].values())
assert all(v==0 for v in black['raw_cfa_means'].values())
d.update(expected_neutral_uv=[128,128],rounding_tolerance_codes=1,
         white_and_black_patch_neutrality_pass=False,color_processing_requires_fix=True,
         observed_white_uv=[white['u_mean'],white['v_mean']],observed_black_uv=[black['u_mean'],black['v_mean']],
         root_cause_not_yet_identified=True,gamma_dmi_channel_layout_and_input_domain_need_investigation=True)
assert any(abs(v-128)>1 for v in d['observed_white_uv']) and any(abs(v-128)>1 for v in d['observed_black_uv'])
p.write_text(json.dumps(d,indent=2)+'\n')
print('Recorded actual white/black neutrality failure; no calibration or hardware ISP completion claim.')
