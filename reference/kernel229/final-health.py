"""Repeat the current228-boot audit after daylight capture, keeping all guards."""
from pathlib import Path
import ast
import json
import host

ref = Path(__file__).resolve().parent
source = ast.parse((ref.parent / 'kernel228/final-health.py').read_text())
node = next(n for n in source.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'code' for t in n.targets))
code = ast.literal_eval(node.value)
assert code.count("out=root/'k228-final-health'") == 1
code = code.replace("out=root/'k228-final-health'", "out=root/'k229-final-health'")
code = code.replace('report=dict(stage=228,', 'report=dict(stage=229,')
result = host.ssh('python3 -', input=code.encode(), timeout=100)
(host.PRIVATE / 'final-health-host-private.log').write_bytes(result.stdout + result.stderr)
report = json.loads(result.stdout)
report.update(daylight32_rgb_and6raw6rgb_completed=True, scene_images_saved=False,
              original_camera_controls_formats_graph_restored=True)
(ref / 'final-health-validation.json').write_text(json.dumps(report, indent=2) + '\n')
state = json.loads((host.PRIVATE / 'current-work-private.json').read_text())
state.update(state='daylight32 RGB channel stats and6raw6rgb passed; all camera state restored; final current boot health passed with known OOT4096',
             active_native_session=None,active_native_context=None,transition_pending=False,
             next='Close docs/evidence then clean controlled boot of staged2abde intree module; true colour accuracy/CFA still open')
(host.PRIVATE / 'current-work-private.json').write_text(json.dumps(state, indent=2) + '\n')
print(json.dumps(report))
