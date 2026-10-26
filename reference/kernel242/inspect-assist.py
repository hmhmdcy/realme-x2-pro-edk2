from pathlib import Path
import json
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
watch=json.loads((r/'gnss-assist/watch-state.json').read_text())
safe={k:v for k,v in watch.items() if isinstance(v,(bool,int,float)) or v is None}
print(json.dumps(dict(report=dict(stage=242,watch_numeric_state=safe),private=watch)))
