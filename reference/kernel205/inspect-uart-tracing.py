from pathlib import Path
import json

root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k205-baseline/boot-id-private.txt').read_bytes()
out=root/'k205-uart-trace-inspection';assert not out.exists();out.mkdir(mode=0o700)
base=Path('/sys/kernel/tracing/events/qcom_geni_serial');events=[p.name for p in base.iterdir() if p.is_dir()] if base.exists() else []
for p in base.glob('*/format'):(out/(p.parent.name+'-format-private.txt')).write_bytes(p.read_bytes())
r=dict(stage=205,available_geni_trace_events=events,debug_trace_instances_available=Path('/sys/kernel/tracing/instances').is_dir(),no_trace_enabled=True)
(out/'summary.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
